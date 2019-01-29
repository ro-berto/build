#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to create a compilation index pack and upload it to Google Storage."""


import argparse
import errno
import fnmatch
import hashlib
import itertools
import json
import os
import re
import shutil
import shlex
import sys
import tempfile
import time
import zipfile

from contextlib import closing


class IndexPack(object):
  """Class used to create an index pack to be indexed by Kythe."""

  def __init__(self, compdb_path, corpus=None, root=None,
               out_dir='src/out/Debug', verbose=False):
    """Initializes IndexPack.

    Args:
      compdb_path: path to the compilation database.
      corpus: the corpus to use for the generated Kythe VNames, e.g. 'chromium'.
        A VName identifies a node in the Kythe index. For more details, see:
        https://kythe.io/docs/kythe-storage.html
      root: the root to use for the generated Kythe VNames (optional)
      out_dir: The output directory from which compilation was run.
    """
    if corpus is None:
      raise Exception('ERROR: --corpus required')

    with open(compdb_path, 'rb') as json_commands_file:
      # The list of JSON dictionaries, each describing one compilation unit.
      self.json_dictionaries = json.load(json_commands_file)
    self.corpus = corpus
    self.root = root
    self.out_dir = out_dir
    self.verbose = verbose
    # Maps from source file name to the SHA256 hash of its content.
    self.filehashes = {}
    # Create a temporary data directory. The structure is as follows:
    # A root directory (arbitrary name) with two subdirectories. The
    # subdirectory 'files' should contain all source files involved in any
    # compilation unit. The subdirectory 'units' describes the compilation units
    # in JSON format.
    self.index_directory = tempfile.mkdtemp()
    print 'Storing the index pack files in ' + self.index_directory
    # Path for the files directory within the index directory
    self.files_directory = os.path.join(self.index_directory, 'files')
    # Path for the units directory within the index directory
    self.units_directory = os.path.join(self.index_directory, 'units')
    os.makedirs(self.files_directory)
    os.makedirs(self.units_directory)

  def close(self):
    """Cleans up any temporary dirs created in the constructor."""
    shutil.rmtree(self.index_directory)

  def _GenerateDataFiles(self):
    """A function which produces the data files for the index pack.

    Each file is a copy of a source file which is needed for at least one
    compilation unit.
    """

    # Keeps track of the '*.filepaths' files already processed.
    filepaths = set()
    # Process all entries in the compilation database.
    for entry in self.json_dictionaries:
      filepath = os.path.join(entry['directory'], entry['file'] + '.filepaths')
      if self.verbose:
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
          # We should not package builtin clang header files, see
          # crbug.com/513826
          if 'third_party/llvm-build' in fname:
            continue
          if fname not in self.filehashes:
            # We don't want to fail completely if the file doesn't exist.
            if not os.path.exists(fname):
              print 'missing ' + fname
              continue
            # Derive the new filename from the SHA256 hash.
            with open(fname, 'rb') as source_file:
              content = source_file.read()
            content_hash = hashlib.sha256(content).hexdigest()
            self.filehashes[fname] = content_hash
            file_name = os.path.join(self.files_directory, content_hash)
            if self.verbose:
              print ' Including source file %s as %s for compilation' % (
                  fname, file_name)
            with open(file_name, 'wb') as f:
              f.write(content)

  def _GenerateUnitFiles(self):
    """A function which produces the unit files for the index pack.

    A unit file consists of a JSON dump of this format:
    {
      'source_file': [<name of the cc or c file>],
      'output_key': <path to the file generated by this compilation unit>,
      'argument': <list of compilation parameters>,
      'v_name': {
        'corpus': <a corpus such as chromium>,
        'root': <a build config such as chromium-linux>,
      },
      'required_input': [
        {
          'v_name': {
            'corpus': <a corpus such as chromium>,
            'root': <a build config such as chromium-linux>,
            'path': '<path to the source file relative to the root and with
                      relativizing particles ('.', '..') removed>
          },
          'info': {
            'path': <path to the source file>,
            'digest': <SHA256 hash of the contents of the source file>,
          }
        },
        ...
      ]
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

      # Remove warning flags from the command. These are disabled later by
      # appending -w anyway, so there's no need to bloat the index pack with
      # them.
      compile_command = _RemoveWarningSwitches(entry['command'])

      if self.verbose:
        print 'Generating Translation Unit data for %s' % entry['file']
        print 'Compile command: %s' % compile_command

      command_list = shlex.split(compile_command, posix=sys.platform != 'win32')
      # On some platforms, the |command_list| starts with the goma executable,
      # followed by the path to the clang executable (either clang++ or
      # clang-cl.exe). We want the clang executable to be the first parameter.
      for i in range(len(command_list)):
        if 'clang' in command_list[i]:
          # Shorten the list of commands such that it starts with the path to
          # the clang executable.
          command_list = command_list[i:]
          break

      # Extract the output file argument
      output_file = None
      for i in range(len(command_list)):
        if command_list[i] == '-o' and i + 1 < len(command_list):
          output_file = command_list[i + 1]
          break
        elif command_list[i].startswith('/Fo'):
          # Handle the Windows case.
          output_file = command_list[i][len('/Fo'):]
          break
      if not output_file:
        print 'No output file path found for %s' % entry['file']

      required_inputs = []
      with open(filepath, 'rb') as filepaths_file:
        for line in filepaths_file:
          fname = line.strip()
          # We should not package builtin clang header files, see
          # crbug.com/513826
          if 'third_party/llvm-build' in fname:
            continue
          # The clang tool uses '//' to separate the system path where system
          # headers can be found from the relative path used in the #include
          # statement.
          if '//' in fname:
            path = fname.split('//')
            fname = '/'.join(path)
          fname_fullpath = os.path.join(entry['directory'], fname)
          if fname_fullpath not in self.filehashes:
            print 'No information about required input file %s' % fname_fullpath
            continue

          # Handle absolute paths - when normalizing we assume paths are
          # relative to the output directory (e.g. src/out/Debug).
          if os.path.isabs(fname):
            fname = os.path.relpath(fname, entry['directory'])

          normalized_fname = os.path.normpath(os.path.join(self.out_dir, fname))
          required_input = {
              'v_name': {
                  'corpus': self.corpus,
                  'path': normalized_fname,
              }
          }

          # Add the VName root only if it was specified.
          if self.root:
            required_input['v_name']['root'] = self.root

          required_input['info'] = {
              'path': fname,
              'digest': self.filehashes[fname_fullpath],
          }

          required_inputs.append(required_input)

      unit_dictionary['source_file'] = [entry['file']]
      unit_dictionary['output_key'] = output_file
      unit_dictionary['v_name'] = {
          'corpus': self.corpus,
          'language': 'c++',
      }
      # Add the VName root only if it was specified.
      if self.root:
        unit_dictionary['v_name']['root'] = self.root

      # Disable all warnings with -w so that the indexer can run successfully.
      # The job of the indexer is to index the code, not to verify it. Warnings
      # we actually care about should show up in the compile step.
      unit_dictionary['argument'] = command_list + ['-w']
      unit_dictionary['required_input'] = required_inputs

      if self.verbose:
        print "Unit argument: %s" % unit_dictionary['argument']

      wrapper = {
          'unit': unit_dictionary
      }

      # Dump the dictionary in JSON format.
      unit_file_content = json.dumps(wrapper)
      unit_file_content_hash = hashlib.sha256(unit_file_content).hexdigest()
      unit_file_path = os.path.join(self.units_directory,
                                    unit_file_content_hash)
      with open(unit_file_path, 'wb') as unit_file:
        unit_file.write(unit_file_content)
      if self.verbose:
        print 'Wrote compilation unit file %s' % unit_file_path

  def GenerateIndexPack(self):
    """Generates the index pack.

    An index pack consists of data files (the source and header files) and unit
    files (describing one compilation unit each).
    """

    # Generate the source files.
    # This needs to be called first before calling _GenerateUnitFiles()
    self._GenerateDataFiles()

    # Generate the unit files.
    self._GenerateUnitFiles()

  def CreateArchive(self, filepath):
    """Creates a zip archive containing the index pack.

    Args:
      filepath: The filepath where the index pack archive should be stored.
    Raises:
      Exception: The zip command failed to create the archive
    """

    # Remove the old zip archive (if it exists). This avoids that the new index
    # pack is just added to the old zip archive.
    if os.path.exists(filepath):
      os.remove(filepath)

    # We use zipfile here rather than shutil.make_archive because it has a bug
    # on Python <2.7.11 where it doesn't add entries for directories (see
    # https://bugs.python.org/issue24982).
    # TODO(crbug/790616): Once the bots have been migrated to LUCI, the block
    # below can be replaced with shutil.make_archive.
    with zipfile.ZipFile(
        filepath, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
      # os.walk doesn't include the directory you point it at in its output.
      archive.write(self.index_directory,
                    os.path.basename(self.index_directory))

      for root, dirnames, filenames in os.walk(self.index_directory):
        for filename in itertools.chain(dirnames, filenames):
          # The format specification requires that the archive contains one
          # folder with an arbitrary name directly containing the 'units' and
          # 'files' directories. So, if index_directory is foo/bar, we need to
          # prefix all the filenames with bar/. We do this by taking the path
          # relative to the parent of the index directory.
          abs_path = os.path.join(root, filename)
          index_parent = os.path.dirname(self.index_directory.rstrip(os.sep))
          rel_path = os.path.relpath(abs_path, index_parent)
          archive.write(abs_path, rel_path)


WARNING_SWITCH_RE = re.compile(r'\s[-/][Ww]\S+')


def _RemoveWarningSwitches(cmd_str):
  """Removes all warning switches from a command string."""
  return re.sub(WARNING_SWITCH_RE, '', cmd_str)


def _RemoveFilepathsFiles(root):
  """Removes all .filepaths files within specified root dir."""
  for path, _, files in os.walk(os.path.abspath(root)):
    for filename in fnmatch.filter(files, '*.filepaths'):
      try:
        os.remove(os.path.join(path, filename))
      except OSError, e:
        if e.errno != errno.ENOENT:
          raise


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--path-to-archive-output',
                      required=True,
                      help='path to index pack archive to be generated')
  parser.add_argument('--path-to-compdb',
                      required=True,
                      help='path to the compilation database')
  parser.add_argument('--corpus',
                      default='chromium-linux',
                      help='the kythe corpus to use for the vname')
  parser.add_argument('--root',
                      help='the kythe root to use for the vname')
  parser.add_argument('--out_dir',
                      default='src/out/Debug',
                      help='the output directory from which compilation is run')
  parser.add_argument('--keep-filepaths-files',
                      help='keep the .filepaths files used for index pack '
                      'generation',
                      action='store_true')
  parser.add_argument('--verbose',
                      help='print details of every file being written to the '
                      'index pack.',
                      action='store_true')
  options = parser.parse_args()

  print '%s: Index generation...' % time.strftime('%X')
  with closing(IndexPack(options.path_to_compdb, options.corpus, options.root,
                         options.out_dir, options.verbose)) as index_pack:
    index_pack.GenerateIndexPack()

    if not options.keep_filepaths_files:
      # Clean up the *.filepaths files.
      _RemoveFilepathsFiles(os.path.join(os.getcwd(), 'src'))

    # Create the archive containing the generated files.
    index_pack.CreateArchive(options.path_to_archive_output)

  print '%s: Done.' % time.strftime('%X')
  return 0


if '__main__' == __name__:
  sys.exit(main())
