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
from windows_shell_split import WindowsShellSplit


class IndexPack(object):
  """Class used to create an index pack to be indexed by Kythe."""

  def __init__(self, root_dir, compdb_path, gn_targets_path, corpus=None,
               root=None, build_config=None, out_dir='src/out/Debug',
               verbose=False):
    """Initializes IndexPack.

    Args:
      root_dir: path to the root of the checkout (i.e. the path containing
        src/). out_dir is relative to this.
      compdb_path: path to the compilation database.
      gn_targets_path: path to a json file contains gn target information, as
        produced by 'gn desc --format=json'. See 'gn help desc' for more info.
      corpus: the corpus to use for the generated Kythe VNames, e.g. 'chromium'.
        A VName identifies a node in the Kythe index. For more details, see:
        https://kythe.io/docs/kythe-storage.html
      root: the root to use for the generated Kythe VNames (optional)
      build_config: the build config to specify in the unit file, e.g. 'android'
        or 'windows' (optional)
      out_dir: The output directory from which compilation was run.
    """
    if corpus is None:
      raise Exception('ERROR: --corpus required')

    with open(compdb_path, 'rb') as json_commands_file:
      # The list of JSON dictionaries, each describing one compilation unit.
      self.compdb = json.load(json_commands_file)
    with open(gn_targets_path, 'rb') as json_gn_targets_file:
      gn_targets_dict = json.load(json_gn_targets_file)

      # We only care about certain mojom targets. Filter it down here so we
      # don't need to do so both times we iterate over it.
      self.mojom_targets = [
          # Flatten targets with multiple sources. Invoking the bindings
          # generator with multiple files is equivalent to invoking it on each
          # of those files individually in sequence.
          dict(gn_target, sources=[source])
          for gn_target in gn_targets_dict.itervalues()
          if self._IsMojomTarget(gn_target)
          for source in gn_target['sources']
      ]

    self.root_dir = root_dir
    self.corpus = corpus
    self.root = root
    self.build_config = build_config
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

  def _IsMojomTarget(self, gn_target):
    """Predicate to check if a GN target is a Mojom target.

    Note that there are multiple GN targets for each Mojom build rule, due to
    how the mojom.gni rules are defined. We pick a single canonical one out of
    this set, namely the __generator target, which generates the standard C++
    bindings."""
    return (
        'script' in gn_target and
        gn_target['script'].endswith('/mojom_bindings_generator.py') and
        'generate' in gn_target['args'] and
        '--variant' not in gn_target['args'] and
        '--generate_non_variant_code' not in gn_target['args'] and
        # For now we don't support xrefs for languages other than C++, so
        # the mojom analyzer only bothers with the C++ output.
        any(gn_target['args'][i:i + 2] == ['-g', 'c++']
            for i in range(len(gn_target['args']) - 1)) and
        '--generate_message_ids' not in gn_target['args'])

  def close(self):
    """Cleans up any temporary dirs created in the constructor."""
    shutil.rmtree(self.index_directory)

  def _AddDataFile(self, fname):
    """Adds a data file to the archive.

    Adds it into the list of filehashes, and writes it into the kzip with the
    appropriate name."""
    fname = os.path.normpath(fname)

    if fname not in self.filehashes:
      # We don't want to fail completely if the file doesn't exist.
      if not os.path.exists(fname):
        print 'missing ' + fname
        return
      # Derive the new filename from the SHA256 hash.
      with open(fname, 'rb') as source_file:
        content = source_file.read()
      content_hash = hashlib.sha256(content).hexdigest()
      self.filehashes[fname] = content_hash
      hash_fname = os.path.join(self.files_directory, content_hash)
      if self.verbose:
        print ' Including source file %s as %s for compilation' % (fname,
                                                                   hash_fname)
      with open(hash_fname, 'wb') as f:
        f.write(content)

  def _AddUnitFile(self, unit_dictionary):
    if self.verbose:
      print "Unit argument: %s" % unit_dictionary['argument']

    wrapper = {'unit': unit_dictionary}

    # Dump the dictionary in JSON format.
    unit_file_content = json.dumps(wrapper)
    unit_file_content_hash = hashlib.sha256(unit_file_content).hexdigest()
    unit_file_path = os.path.join(self.units_directory,
                                  unit_file_content_hash)
    with open(unit_file_path, 'wb') as unit_file:
      unit_file.write(unit_file_content)
    if self.verbose:
      print 'Wrote compilation unit file %s' % unit_file_path

  def _ConvertGnPath(self, gn_path):
    """Converts gn paths into output-directory-relative paths.

    gn paths begin with a //, which represents the root of the repository."""
    return os.path.relpath(os.path.join('src', *gn_path[2:].split('/')),
                           self.out_dir)

  def _NormalisePath(self, path):
    """Normalise a path.

    For our purposes, "normalised" means relative to the root dir (the one
    containing src/), and passed through os.path.normpath (which eliminates
    double slashes, unnecessary '.' and '..'s, etc.
    """

    return os.path.normpath(os.path.join(self.out_dir, path))

  def _CorrespondingGeneratedHeader(self, gn_target):
    """Given a mojom gn target, return the corresponding generated header
    filename.

    e.g. //foo/bar.mojom -> gen/foo/bar.mojom.h
    """

    source_mojom = gn_target['sources'][0]
    return 'gen/%s.h' % source_mojom[len('//'):]

  def _GenerateDataFiles(self):
    """A function which produces the data files for the index pack.

    Each file is a copy of a source file which is needed for at least one
    compilation unit.
    """

    # Keeps track of the '*.filepaths' files already processed.
    filepaths = set()
    for entry in self.compdb:
      filepaths_fn = os.path.join(entry['directory'],
                                  entry['file'] + '.filepaths')
      if self.verbose:
        print 'Extract source files from %s' % filepaths_fn

      # We don't want to fail if one of the filepaths doesn't exist. However we
      # keep track of it.
      if not os.path.exists(filepaths_fn):
        print 'missing ' + filepaths_fn
        continue

      # For some reason, the compilation database contains the same targets more
      # than once. However we have just one file containing the file paths of
      # the involved files. So we can skip this entry if we already processed
      # it.
      if filepaths_fn in filepaths:
        continue
      filepaths.add(filepaths_fn)

      # All file paths given in the *.filepaths file are either absolute paths
      # or relative to the directory entry in the compilation database.
      with open(filepaths_fn, 'rb') as filepaths_file:
        # Each line in the '*.filepaths' file references the path to a source
        # file involved in the compilation.
        for line in filepaths_file:
          fname = os.path.join(entry['directory'],
                               line.strip().replace('//', '/'))
          # We should not package builtin clang header files, see
          # crbug.com/513826
          if 'third_party/llvm-build' in fname:
            continue

          self._AddDataFile(fname)

    for target in self.mojom_targets:
      # Add the .mojom file itself.
      self._AddDataFile(
          os.path.join(self.root_dir, self.out_dir,
                       self._ConvertGnPath(target['sources'][0])))

      # Add the C++ header file generated from this mojom file. The Kythe mojom
      # analyser can't generate this itself, so it needs it supplied in order to
      # wire up the mojom identifiers to their generated C++ counterparts.
      self._AddDataFile(
          os.path.join(self.root_dir, self.out_dir,
                       self._CorrespondingGeneratedHeader(target)))

  def _GenerateUnitFiles(self):
    """Produces the unit files for the index pack.

    A unit file consists of a JSON dump of this format:
    {
      'source_file': [<name of the cc, c, or mojom file>],
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

    for entry in self.compdb:
      filepaths_fn = os.path.join(entry['directory'],
                                  entry['file'] + '.filepaths')
      if not os.path.exists(filepaths_fn) or filepaths_fn in filepaths:
        continue
      filepaths.add(filepaths_fn)

      # Add two unit files: one with the build config in the root, and one with
      # it in the new build config fields. The new one also has a new corpus
      # name.
      # TODO(jsca): Remove the legacy unit when nothing is using the old format.
      self._AddClangUnitFile(entry['file'], entry['directory'],
                             entry['command'], filepaths_fn,
                             'chromium',  # legacy corpus name
                             root=self.root, build_config=None)
      self._AddClangUnitFile(entry['file'], entry['directory'],
                             entry['command'], filepaths_fn, self.corpus,
                             root=None, build_config=self.build_config)


    for target in self.mojom_targets:
      unit_dictionary = {}

      source_file = self._ConvertGnPath(target['sources'][0])
      unit_dictionary['source_file'] = [source_file]
      generated_header = self._CorrespondingGeneratedHeader(target)
      unit_dictionary['output_key'] = generated_header

      # gn produces an unsubstituted {{response_file_name}} for filelist. We
      # can't work with this, so we remove it and add the source file as a
      # positional argument instead.
      unit_dictionary['argument'] = [
          arg for arg in target['args'] if not arg.startswith('--filelist=')
      ] + [source_file]

      unit_dictionary['v_name'] = {
          'corpus': self.corpus,
          'language': 'mojom',
      }
      if self.build_config:
        unit_dictionary['details'] = {
            '@type': 'kythe.io/proto/kythe.proto.BuildDetails',
            'build_config': self.build_config,
        }

      # TODO(orodley): In order to do name resolution we'll need to add all the
      # files that are directly referenced (not the full transitive closure
      # though).
      required_inputs = []
      for required_file in [source_file, generated_header]:
        path = os.path.normpath(
            os.path.join(self.root_dir, self.out_dir, required_file))
        # We don't want to fail completely if the file doesn't exist.
        if path not in self.filehashes:
          print 'missing from filehashes %s' % path
          continue

        required_input = {
            'v_name': {
                'corpus': self.corpus,
                'path': self._NormalisePath(required_file),
            },
            'info': {
                'path': required_file,
                'digest': self.filehashes[path],
            },
        }

        required_inputs.append(required_input)
      unit_dictionary['required_input'] = required_inputs

      self._AddUnitFile(unit_dictionary)

  def _AddClangUnitFile(self, filename, directory, command, filepaths_fn,
                        corpus, root=None, build_config=None):
    """Adds a unit file based on the output of the clang translation_unit tool.

    Args:
      filename: The relative path to the source file from the output directory.
      directory: The output directory (e.g. src/out/Debug).
      command: The command line used to run the compilation.
      filepaths_file: Path to the .filepaths file for this compilation, which
        contains a list of all the required dependency files.
      corpus: The corpus to specify in the unit file.
      root: The root to specify in the unit file, if any.
      build_config: The build config to specify in the unit file, if any.
    """
    # For each compilation unit, generate a dictionary in the format described
    # above.
    unit_dictionary = {}

    # Remove warning flags from the command. These are disabled later by
    # appending -w anyway, so there's no need to bloat the index pack with
    # them.
    compile_command = _RemoveWarningSwitches(command)

    if self.verbose:
      print 'Generating Translation Unit data for %s' % filename
      print 'Compile command: %s' % compile_command

    command_list = _ShellSplit(compile_command)
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
      print 'No output file path found for %s' % filename

    # Convert any args starting with -imsvc to use forward slashes, since this
    # is what Kythe expects.
    if sys.platform == 'win32':
      for i in range(len(command_list)):
        if command_list[i].startswith('-imsvc'):
          command_list[i] = command_list[i].replace('\\', '/')
      # HACK ALERT: Here we define header guards to prevent Kythe from using
      # the CUDA wrapper headers, which cause indexing errors.
      # The standard Kythe extractor dumps header search state to help the
      # indexer find the right headers, but we don't do that in this script.
      # The below lines work around it by excluding the CUDA headers entirely.
      command_list += [
          '-D__CLANG_CUDA_WRAPPERS_NEW',
          '-D__CLANG_CUDA_WRAPPERS_COMPLEX',
          '-D__CLANG_CUDA_WRAPPERS_ALGORITHM',
      ]

    required_inputs = []
    with open(filepaths_fn, 'rb') as filepaths_file:
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
        fname_fullpath = os.path.normpath(
            os.path.join(directory, fname))
        if fname_fullpath not in self.filehashes:
          print 'No information about required input file %s' % fname_fullpath
          continue

        # Handle absolute paths - when normalizing we assume paths are
        # relative to the output directory (e.g. src/out/Debug).
        if os.path.isabs(fname):
          fname = os.path.relpath(fname, directory)

        normalized_fname = self._NormalisePath(fname)
        if sys.platform == 'win32':
          # Kythe expects all paths to use forward slashes.
          normalized_fname = normalized_fname.replace('\\', '/')
        required_input = {
            'v_name': {
                'corpus': corpus,
                'path': normalized_fname,
            }
        }

        # Add the VName root only if it was specified.
        if root:
          required_input['v_name']['root'] = root

        if sys.platform == 'win32':
          # Kythe expects all paths to use forward slashes.
          fname = fname.replace('\\', '/')
        required_input['info'] = {
            'path': fname,
            'digest': self.filehashes[fname_fullpath],
        }

        required_inputs.append(required_input)

    unit_dictionary['source_file'] = [filename]
    unit_dictionary['output_key'] = output_file
    unit_dictionary['v_name'] = {
        'corpus': corpus,
        'language': 'c++',
    }
    # Add the VName root only if it was specified.
    if root:
      unit_dictionary['v_name']['root'] = root
    # Add the build config if specified.
    if build_config:
      unit_dictionary['details'] = {
          '@type': 'kythe.io/proto/kythe.proto.BuildDetails',
          'build_config': build_config,
      }

    # Disable all warnings with -w so that the indexer can run successfully.
    # The job of the indexer is to index the code, not to verify it. Warnings
    # we actually care about should show up in the compile step.
    unit_dictionary['argument'] = command_list + ['-w']
    unit_dictionary['required_input'] = required_inputs

    self._AddUnitFile(unit_dictionary)


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


def _ShellSplit(command):
  """Splits a shell command into separate args."""
  if sys.platform == 'win32':
    return WindowsShellSplit(command)
  else:
    return shlex.split(command)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--path-to-archive-output',
                      required=True,
                      help='path to index pack archive to be generated')
  parser.add_argument('--path-to-compdb',
                      required=True,
                      help='path to the compilation database')
  parser.add_argument('--path-to-gn-targets',
                      required=True,
                      help='path to the gn targets json file')
  parser.add_argument('--corpus',
                      default='chromium-linux',
                      help='the kythe corpus to use for the vname')
  parser.add_argument('--root',
                      help='the kythe root to use for the vname')
  parser.add_argument('--build-config',
                      help='the build config to use in the unit file')
  parser.add_argument('--checkout-dir',
                      required=True,
                      help='The root of the repository.')
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

  root_dir = os.path.normpath(os.path.join(options.checkout_dir, '..'))

  print '%s: Index generation...' % time.strftime('%X')
  with closing(
      IndexPack(root_dir, options.path_to_compdb, options.path_to_gn_targets,
                options.corpus, options.root, options.build_config,
                options.out_dir, options.verbose)) as index_pack:
    index_pack.GenerateIndexPack()

    if not options.keep_filepaths_files:
      # Clean up the *.filepaths files.
      _RemoveFilepathsFiles(os.path.join(root_dir, 'src'))

    # Create the archive containing the generated files.
    index_pack.CreateArchive(options.path_to_archive_output)

  print '%s: Done.' % time.strftime('%X')
  return 0


if '__main__' == __name__:
  sys.exit(main())
