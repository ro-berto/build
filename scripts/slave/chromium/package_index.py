#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to create a compilation index pack and upload it to Google Storage."""


import argparse
import gzip
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time

from common import chromium_utils


class IndexPack(object):

  def __init__(self, compdb_path):
    with open(compdb_path, 'rb') as json_commands_file:
      # The list of JSON dictionaries, each describing one compilation unit.
      self.json_dictionaries = json.load(json_commands_file)
    # Maps from source file name to the SHA256 hash of its content.
    self.filehashes = {}
    # Maps from source file name to the file size.
    self.filesizes = {}
    # Create a temporary data directory. The structure is as follows:
    # A root directory (arbitrary name) with two subdirectories. The
    # subdirectory 'files' should contain all source files (compressed with
    # gzip) involved in any compilation unit. The subdirectory 'units'
    # describes the compilation units in JSON format (also compressed with
    # gzip).
    self.index_directory = tempfile.mkdtemp()
    print 'Storing the index pack files in ' + self.index_directory
    # Path for the files directory within the index directory
    self.files_directory = os.path.join(self.index_directory, 'files')
    # Path for the units directory within the index directory
    self.units_directory = os.path.join(self.index_directory, 'units')
    os.makedirs(self.files_directory)
    os.makedirs(self.units_directory)

  def _GenerateDataFiles(self):
    """A function which produces the data files for the index pack.

    Each '*.data' file corresponds to a source file which is needed for at least
    one compilation unit. It contains gzip compressed contents of the source
    file.
    """

    # Keeps track of the '*.filepaths' files already processed.
    filepaths = set()
    # Process all entries in the compilation database.
    for entry in self.json_dictionaries:
      filepath = os.path.join(entry['directory'], entry['file'] + '.filepaths')
      print 'Extract source files from %s' % filepath

      # We don't want to fail if one of the filepaths doesn't exist. However we
      # keep track of it.
      if not os.path.exists(filepath):
        print 'missing ' + filepath
        continue

      # For some reason, the compilation database contains the same targets more
      # than once. However we have just one file containing the file paths of
      # the involved files. So we can skip this entry if we already processed
      # it.
      if filepath in filepaths:
        continue
      filepaths.add(filepath)

      # All file paths given in the *.filepaths file are either absolute paths
      # or relative to the directory entry in the compilation database.
      with open(filepath, 'rb') as filepaths_file:
        # Each line in the '*.filepaths' file references the path to a source
        # file involved in the compilation.
        for line in filepaths_file:
          fname = os.path.join(entry['directory'],
                               line.strip().replace('//', '/'))
          if not fname in self.filehashes:
            # Derive the new filename from the SHA256 hash.
            with open(fname, 'rb') as source_file:
              content = source_file.read()
            content_hash = hashlib.sha256(content).hexdigest()
            self.filehashes[fname] = content_hash
            self.filesizes[fname] = len(content)
            compressed_file_name = os.path.join(
                self.files_directory, content_hash + '.data')
            with gzip.open(compressed_file_name, 'wb') as compressed_file:
              compressed_file.writelines(content)

  def _GenerateUnitFiles(self):
    """A function which produces the unit files for the index pack.

    A unit file consists of a gzip compressed JSON dump of the following kind of
    dictionary:
    {
      'analysis_target': <name of the cc or c file>,
      'argument': <list of compilation parameters>,
      'cxx_arguments': {},
      'required_input': <list of input file dictionaries>
    }
    The input file dictionary looks like this:
    {
      'path': <path to the source file>,
      'size': <size of the source file>,
      'digest': <SHA256 hash of the contents of the source file>
    }
    """

    # Keeps track of the '*.filepaths' files already processed.
    filepaths = set()

    # Process all entries in the compilation database.
    for entry in self.json_dictionaries:
      filepath = os.path.join(entry['directory'], entry['file'] + '.filepaths')
      if not os.path.exists(filepath) or filepath in filepaths:
        continue
      filepaths.add(filepath)

      # For each compilation unit, generate a dictionary in the format described
      # above.
      unit_dictionary = {}
      unit_dictionary['analysis_target'] = entry['file']
      unit_dictionary['cxx_arguments'] = {}
      print 'Generating Translation Unit data for %s' % entry['file']

      command_list = entry['command'].split()
      # The |command_list| starts with the compiler that was used for the
      # compilation. In the unit file we want to have just the parameters passed
      # to the compiler (which always needs to be clang/clang++). Currently,
      # |command_list| starts with the path to the goma executable followed by
      # the path to the clang executable, but it is safe to assume that the
      # first entry in the list after the clang executable will be the first
      # real parameter.
      for i in range(len(command_list)):
        if 'clang' in command_list[i]:
          # Shorten the list of commands such that it starts after the path to
          # the clang executable with the first real parameter.
          command_list = command_list[i + 1:]
          break

      required_inputs = []
      include_paths = set()
      with open(filepath, 'rb') as filepaths_file:
        for line in filepaths_file:
          fname = line.strip()
          # The clang tool uses '//' to separate the system path where system
          # headers can be found from the relative path used in the #include
          # statement.
          if '//' in fname:
            path = fname.split('//')
            include_paths.add('-isystem%s' % os.path.normpath(path[0]))
            fname = '/'.join(path)
          fname_fullpath = os.path.join(entry['directory'], fname)
          if fname_fullpath not in self.filesizes:
            print 'No information about required input file %s' % fname_fullpath
            continue
          required_input = {
              # Note that although the paths seem to contain redundancy (e. g.
              # '/path/to/lib/../include') we can't use os.path.normpath() here,
              # otherwise the indexer will not work.
              'path': fname,
              'size': self.filesizes[fname_fullpath],
              'digest': self.filehashes[fname_fullpath]
          }
          required_inputs.append(required_input)
      # Add the include paths to the list of compile arguments; also disable all
      # warnings so that the indexer can run successfully. The job of the
      # indexer is to index the code, not to verify it. Warnings we actually
      # care about would show up in the compile step.
      unit_dictionary['argument'] = list(include_paths) + ['-w'] + command_list
      unit_dictionary['required_input'] = required_inputs
      wrapper = {
          'format': 'grok',
          'content': unit_dictionary
      }

      # Dump the dictionary in JSON format to a gzip compressed file.
      unit_file_content = json.dumps(wrapper)
      unit_file_content_hash = hashlib.sha256(unit_file_content).hexdigest()
      unit_file_path = os.path.join(
          self.units_directory, unit_file_content_hash + '.unit')
      with gzip.open(unit_file_path, 'wb') as unit_file:
        unit_file.writelines(unit_file_content)

  def GenerateIndexPack(self):
    """Generates the index pack.

    An index pack consists of data files (the source and header files) and unit
    files (describing one compilation unit each).
    """

    # Generate the compressed source files (*.data).
    # This needs to be called first before calling _GenerateUnitFiles()
    self._GenerateDataFiles()

    # Generate the compressed unit files (*.unit).
    self._GenerateUnitFiles()

  def CreateArchive(self, filepath):
    """Creates a gzipped archive containing the index pack.

    Args:
      filepath: The filepath where the index pack archive should be stored.
    """

    # Run the command in the parent directory of the index pack and use a
    # relative path for the index pack to get rid of any path prefix. The format
    # specification requires that the archive contains one folder with an
    # arbitrary name directly containing the 'units' and 'files' directories.
    if chromium_utils.RunCommand(
        ['tar', '-czf', filepath, os.path.basename(self.index_directory)],
        cwd=os.path.dirname(self.index_directory)) != 0:
      raise Exception('ERROR: failed to create %s, exiting' % filepath)
    # Remove the temporary index pack directory. If there was no exception so
    # far, the archive has been created successfully, so the temporary index
    # pack directory is not needed anymore.
    shutil.rmtree(self.index_directory)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--path-to-archive-output',
                      default=None, required=True,
                      help='path to index pack archive to be generated')
  parser.add_argument('--path-to-compdb',
                      default=None, required=True,
                      help='path to the compilation database')
  options = parser.parse_args()

  print '%s: Index generation...' % time.strftime('%X')
  index_pack = IndexPack(options.path_to_compdb)
  index_pack.GenerateIndexPack()

  # Clean up the *.filepaths files.
  chromium_utils.RemoveFilesWildcards(
      '*.filepaths', os.path.join(os.getcwd(), 'src'))

  # Create the archive containing the generated files.
  index_pack.CreateArchive(options.path_to_archive_output)

  print '%s: Done.' % time.strftime('%X')
  return 0


if '__main__' == __name__:
  sys.exit(main())
