#!/usr/bin/env vpython
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to create a compilation index pack and upload it to Google Storage."""

from __future__ import absolute_import
from __future__ import print_function

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

from google.protobuf import json_format

from kythe.proto import analysis_pb2, buildinfo_pb2, java_pb2

from windows_shell_split import WindowsShellSplit

# Used for finding required_input for a Mojom target, by finding the imports in
# its source.
# This could possibly have false positives (e.g. if there's an import in a
# C-style multiline comment), but it shouldn't have any false negatives, which
# is more important here.
MOJOM_IMPORT_RE = re.compile(r'^\s*import\s*"([^"]*)"', re.MULTILINE)

# Used for finding required_input for a Proto target, by finding the imports in
# its source. Import spec:
# https://developers.google.com/protocol-buffers/docs/reference/proto3-spec#import_statement
PROTO_IMPORT_RE = re.compile(r'^\s*import\s*(?:weak|public)?\s*"([^"]*)\s*";',
                             re.MULTILINE)

# A list of path prefixes to external corpsus names, used by kythe/grimoire
# to find external headers.
EXTERNAL_CORPORA = [
    ('src/third_party/depot_tools/win_toolchain', 'winsdk'),
    ('src/build/linux/debian_sid_amd64-sysroot', 'debian_amd64'),
]

# Substrings of arguments that should be removed from compile commands on
# Windows.
UNWANTED_ARG_SUBSTRINGS_WIN = [
    # These Skia header path defines throw errors in the Windows indexer for
    # some reason.
    '-DSK_USER_CONFIG_HEADER',
    '-DSK_GPU_WORKAROUNDS_HEADER',
]


def ConvertPathToForwardSlashes(path):
  """Converts a path that may use \ as a path separator to use /.

  Kythe expects all paths to use forward slashes, but if this script is
  running on Windows we may get some backslashes in our paths.
  """
  if sys.platform == 'win32':
    return path.replace('\\', '/')
  return path


def InjectUnitBuildDetails(unit, build_config):
  """InjectUnitBuildDetails adds BuildDetail information into unit."""
  # If there is already BuildDetails, we need to reuse it
  for any_details in unit.details:
    if any_details.type_url == 'kythe.io/proto/kythe.proto.BuildDetails':
      build_details = buildinfo_pb2.BuildDetails()
      build_details.ParseFromString(any_details.value)
      build_details.build_config = build_config
      any_details.Pack(build_details, 'kythe.io/proto')
      return

  # BuildDetails wasn't found, create a new one
  details = buildinfo_pb2.BuildDetails()
  details.build_config = build_config

  details_any_proto = unit.details.add()
  details_any_proto.Pack(details, 'kythe.io/proto')


def ConvertGnPath(gn_path, out_dir):
  """Converts gn paths into output-directory-relative paths.

  gn paths begin with a //, which represents the root of the repository.
  expectation is that out_dir always contains src/"""
  assert out_dir.startswith('src')
  return os.path.relpath(os.path.join('src', *gn_path[2:].split('/')), out_dir)


def FindImports(regex, file_path, import_paths):
  """FindImports looks for all import statements and returns absolute path
  to all imported files.

  Args:
    input: compiled regex that matches import statement. It can have only
    one group which yields import filename
    file_path: path to file that will be inspected, absolute path
    import_paths: list of import directories, should be absolute path

  Returns:
    set containing all imports

  For example, if content of .proto file is following:
  import "foo.proto"
  import weak "bar.proto"

  and working directory is '/tmp' and regex is PROTO_IMPORT_RE

  this function will return set('/tmp/foo.proto', '/tmp/bar.proto')
  """
  imports = set()
  if not os.path.exists(file_path):
    print('file %s does not exist, returning empty import set' % file_path)
    return imports

  with open(file_path, 'r') as f:
    contents = f.read()

  for imp in re.findall(regex, contents):
    for import_path in import_paths:
      path = os.path.join(import_path, imp)
      if os.path.exists(path):
        imports.add(os.path.normpath(path))
        break
    else:
      print('couldn\'t find import %s for file %s.' % (imp, file_path))
      print(import_paths)
  return imports


class ProtoTarget():
  """Class that defines a single proto compilation unit"""

  def __init__(self, gn_target, root_dir, out_dir):
    assert 'sources' in gn_target
    assert out_dir.startswith('src')

    self._all_files = None
    self.sources = gn_target['sources']
    self.args = gn_target['args'] if 'args' in gn_target else []
    self.root_dir = root_dir
    self.out_dir = out_dir

    def construct_normpath(arg_path):
      return os.path.normpath(
          os.path.join(self.root_dir, self.out_dir, arg_path))

    self.proto_paths = [
        construct_normpath(self.args[i + 1])
        for i in range(len(self.args) - 1)
        if self.args[i] == '--proto-in-dir'
    ]

    import_dir_prefix = '--import-dir='
    self.proto_paths += [
        construct_normpath(arg[len(import_dir_prefix):])
        for arg in self.args
        if arg.startswith(import_dir_prefix)
    ]

    if not self.proto_paths:
      self.proto_paths = [os.path.join(self.root_dir, out_dir)]

  def GetFiles(self):
    """Retrieve list of all files that are required for compilation of target

    Returns:
      list of all included files, in their absolute paths
    """
    if self._all_files is None:
      self._all_files = self._FindAllUsedFiles()

    return self._all_files

  def GetUnit(self, corpus, filehashes, build_config=None):
    """Retrieve compulation unit for target

    Args:
      corpus: string
      filehashes: map of filename to hash, to avoid recomputing
      build_config: string

    Returns:
      analysis_pb2.CompilationUnit for target
    """
    unit_proto = analysis_pb2.CompilationUnit()
    source_files = [
        ConvertPathToForwardSlashes(ConvertGnPath(source, self.out_dir))
        for source in self.sources
    ]

    # use sort to make it deterministic, used for unit tests
    for source_file in sorted(source_files):
      unit_proto.source_file.append(source_file)
      # Append to arguments since original source argument needs to be modified.
      unit_proto.argument.append(source_file)

    for arg in self.args:
      # .proto files can be ignored since they are already added.
      if not arg.endswith('.proto'):
        unit_proto.argument.append(arg)

    unit_proto.v_name.corpus = corpus
    unit_proto.v_name.language = 'protobuf'
    if build_config:
      InjectUnitBuildDetails(unit_proto, build_config)

    # use sort to make it deterministic, used for unit tests
    for f in sorted(self.GetFiles()):
      if f not in filehashes:
        # Indexer can't recover from such error so don't bother with unit
        # creation.
        print('WARNING: missing file %s in filehashes, skipping unit '
              'completely.' % f)
        return None
      required_input = unit_proto.required_input.add()
      required_input.v_name.corpus = corpus
      required_input.v_name.path = ConvertPathToForwardSlashes(
          os.path.relpath(os.path.normpath(f), self.root_dir))
      required_input.info.path = ConvertPathToForwardSlashes(
          os.path.relpath(f, os.path.join(self.root_dir, self.out_dir)))
      required_input.info.digest = filehashes[f]

    return unit_proto

  def _FindAllUsedFiles(self):
    """_FindAllUsedFiles walks through all source files and looks for import
    statements.  The process repeats until all imported files are inspected.
    """

    # Use absolute paths as it makes things easier. gn_target sources start
    # with // so that needs to be stripped
    paths = [
        os.path.normpath(
            os.path.join(self.root_dir, self.out_dir,
                         ConvertGnPath(source, self.out_dir)))
        for source in self.sources
    ]
    all_files = set()
    while len(paths):
      path = paths.pop()
      if path in all_files:
        # Already processed, move on
        continue
      all_files.add(path)
      for imp in FindImports(PROTO_IMPORT_RE, path, self.proto_paths):
        paths.append(imp)
    return all_files


class IndexPack(object):
  """Class used to create an index pack to be indexed by Kythe."""

  def __init__(self, output_file, root_dir, compdb_path, gn_targets_path,
               existing_java_kzips, corpus=None, build_config=None,
               out_dir='src/out/Debug', verbose=False):
    """Initializes IndexPack.

    Args:
      output_file: a file-like object or filename to which the index pack will
        be written.
      root_dir: path to the root of the checkout (i.e. the path containing
        src/). out_dir is relative to this.
      compdb_path: path to the compilation database.
      gn_targets_path: path to a json file contains gn target information, as
        produced by 'gn desc --format=json'. See 'gn help desc' for more info.
      existing_java_kzips: path to java kzips produced by javac_extractor. Units
        are in json format.
      corpus: the corpus to use for the generated Kythe VNames, e.g. 'chromium'.
        A VName identifies a node in the Kythe index. For more details, see:
        https://kythe.io/docs/kythe-storage.html
      build_config: the build config to specify in the unit file, e.g. 'android'
        or 'windows' (optional)
      out_dir: The output directory from which compilation was run.
    """
    if corpus is None:
      raise Exception('ERROR: --corpus required')

    if not os.path.isdir(existing_java_kzips):
      raise Exception('ERROR: --existing_java_kzips is not a directory')

    self.root_dir = root_dir
    self.corpus = corpus
    self.existing_java_kzips = existing_java_kzips
    self.build_config = build_config
    self.out_dir = out_dir
    self.verbose = verbose
    self._java_output_set = set()

    # Maps from source file name to the SHA256 hash of its content.
    self.filehashes = {}
    # Maps back from SHA256 hash to source file name. Used to debug cases where
    # duplicate files are added to the zip.
    self.filenames_by_hash = {}

    # Create the kzip. We write data directly into the zip file rather than
    # creating a temporary directory with the structure we want and then zipping
    # it. This reduces the number of IO operations we need. This is particularly
    # beneficial on GCE, as the disk is remote and our IOPS are limited.
    self.kzip = zipfile.ZipFile(
        output_file, 'w', zipfile.ZIP_DEFLATED, allowZip64=True)

    # The structure of the kzip is as follows: A root directory (arbitrary name)
    # with two subdirectories. The subdirectory 'files' should contain all
    # source files involved in any compilation unit. The subdirectory 'units'
    # describes the compilation units in proto format.
    index_directory = 'kzip'
    self.files_directory = os.path.join(index_directory, 'files')
    self.units_directory = os.path.join(index_directory, 'pbunits')

    # Write empty entries for the directories.
    self.kzip.writestr(index_directory + '/', '')
    self.kzip.writestr(self.files_directory + '/', '')
    self.kzip.writestr(self.units_directory + '/', '')

    with open(compdb_path, 'rb') as json_commands_file:
      # The list of JSON dictionaries, each describing one compilation unit.
      self.compdb = json.load(json_commands_file)
    with open(gn_targets_path, 'rb') as json_gn_targets_file:
      gn_targets_dict = json.load(json_gn_targets_file)

      self.mojom_targets = []
      self.proto_targets = []
      for target_name, target in gn_targets_dict.items():
        # We only care about certain mojom targets. Filter it down here so we
        # don't need to do so both times we iterate over it.
        if self._IsMojomTarget(target):
          self.mojom_targets.append(
              dict(
                  target,
                  args=_MergeFeatureArgs(gn_targets_dict, target_name, target),
                  imported_files=self._FindMojomImports(target)))
        elif self._IsProtoTarget(target):
          self.proto_targets.append(
              ProtoTarget(target, self.root_dir, self.out_dir))

  def _IsProtoTarget(self, target):
    return ('script' in target and
            target['script'].endswith('/protoc_wrapper.py'))

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
        '--generate_message_ids' not in gn_target['args'] and
        # TODO(crbug.com/1057746): Fix cross reference support for
        # auto-generated files.
        not any(source.startswith('//out') for source in gn_target['sources']))

  def _FindMojomImports(self, gn_target):
    """Find the direct imports of a Mojom target.

    We do this by using a quick and dirty regex to extract files that are
    actually imported, rather than using the gn dependency structure. A Mojom
    file is allowed to import any file it transitively depends on, which usually
    includes way more files than it actually includes.

    Args:
      gn_target: The GN target for the file to analyse.
    """
    args = gn_target['args']
    import_paths = [
        os.path.normpath(
            os.path.join(self.root_dir, self.out_dir, args[i + 1]))
        for i in range(len(args) - 1)
        if args[i] == '-I'
    ]

    imports = set()
    for source in gn_target['sources']:
      path = os.path.join(self.root_dir, self.out_dir,
                          ConvertGnPath(source, self.out_dir))

      imports |= FindImports(MOJOM_IMPORT_RE, path, import_paths)
    return imports


  def close(self):
    """Closes the underlying zipfile.ZipFile, flushing it to disk."""
    self.kzip.close()

  def _SetFileHashEntry(self, fname, content_hash):
    """Stores the filename and hash in the relevant dicts.

    Returns:
      True if the filehash hasn't been seen before, otherwise False."""
    self.filehashes[fname] = content_hash
    if content_hash in self.filenames_by_hash:
      return False
    self.filenames_by_hash[content_hash] = fname
    return True

  def _AddDataFile(self, fname):
    """Adds a data file to the archive.

    Adds it into the list of filehashes, and writes it into the kzip with the
    appropriate name."""
    fname = os.path.normpath(fname)

    if fname not in self.filehashes:
      # We don't want to fail completely if the file doesn't exist.
      if not os.path.exists(fname):
        print('missing ' + fname)
        return
      # Derive the new filename from the SHA256 hash.
      with open(fname, 'rU') as source_file:
        content = source_file.read()
      content_hash = hashlib.sha256(content).hexdigest()
      # Check if we've already seen this hash before.
      if not self._SetFileHashEntry(fname, content_hash):
        print('WARNING: not including source file:  %s' % fname)
        print('   because it has the same hash as:  %s' %
              self.filenames_by_hash[content_hash])
        return
      hash_fname = os.path.join(self.files_directory, content_hash)
      if self.verbose:
        print(' Including source file %s as %s for compilation' % (fname,
                                                                   hash_fname))
      self.kzip.writestr(hash_fname, content)

  def _AddUnitFile(self, unit_proto):
    if self.verbose:
      print('Unit argument: \n%s' % unit_proto.argument)

    indexed_compilation_proto = analysis_pb2.IndexedCompilation()
    indexed_compilation_proto.unit.CopyFrom(unit_proto)

    # Dump the unit in proto wire format.
    unit_file_content = indexed_compilation_proto.SerializeToString()
    unit_file_content_hash = hashlib.sha256(unit_file_content).hexdigest()
    unit_file_path = os.path.join(self.units_directory,
                                  unit_file_content_hash)
    self.kzip.writestr(unit_file_path, unit_file_content)
    if self.verbose:
      print('Wrote compilation unit file %s' % unit_file_path)


  def _MergeExistingKzips(self):
    # There might be more than one kzip file for the same target. This happens
    # when arguments to javac change and ninja can't remove dynamicly generated
    # kzip file.
    # Sort by modified time, and discard older targets that have the same output
    # key.
    listdir = [
        os.path.join(self.existing_java_kzips, f)
        for f in os.listdir(self.existing_java_kzips)
        if f.endswith('.kzip')
    ]
    listdir.sort(key=os.path.getmtime, reverse=True)
    for f in listdir:
      try:
        with zipfile.ZipFile(
            f, 'r', zipfile.ZIP_DEFLATED, allowZip64=True) as kzip:
          self._MergeExistingKzip(kzip)
      except zipfile.BadZipfile as e:
        # Should there be issue with kzip, skip this unit
        print('Error reading generated zip file %s: %s' % (f, e))
        continue

  def _MergeExistingKzip(self, kzip):
    files = {}
    unit = None

    for zip_info in kzip.infolist():
      # kzip should contain following structure:
      # foo/
      # foo/files
      # foo/files/bar
      # foo/units
      # foo/units/bar
      # We only care for foo/files/* and foo/units/* and we expect only one file
      # in foo/units/ directory
      segments = zip_info.filename.split('/')
      if len(segments) != 3 or segments[-1] == '':
        continue

      if segments[1] == 'units':
        if unit:
          print('Ignoring kzip file as more than one units in kzip file %s.' %
                (zip_info.filename))
          return
        unit = zip_info
      elif segments[1] == 'files':
        files[segments[2]] = zip_info
      else:
        print('WARNING: Unexpected file %s in kzip %s.' % (zip_info.filename,
                                                           kzip.filename))
        return

    if not unit:
      print(
          'Ignoring kzip file %s as unit file is not found.' % (kzip.filename))
      return

    # Add unit file
    try:
      with kzip.open(unit, 'rU') as f:
        content = f.read()
    except zipfile.BadZipfile as e:
      # Should there be issue with extracting kzip, skip this unit
      print('Error reading generated zip file %s: %s' % (kzip.filename, e))
      return

    # Units in Java zip archive are json encoded
    # convert json into a protobuf
    indexed_compilation_proto = json_format.Parse(
        content, analysis_pb2.IndexedCompilation())

    output_key = indexed_compilation_proto.unit.output_key
    if output_key in self._java_output_set:
      print('Duplicated unit "%s" (filename: %s)' % (output_key, kzip.filename))
      return

    self._java_output_set.add(output_key)

    if self.build_config and indexed_compilation_proto.unit:
      InjectUnitBuildDetails(indexed_compilation_proto.unit, self.build_config)

    unit_file_content = indexed_compilation_proto.SerializeToString()
    unit_file_content_hash = hashlib.sha256(unit_file_content).hexdigest()
    unit_file_path = os.path.join(self.units_directory, unit_file_content_hash)
    self.kzip.writestr(unit_file_path, unit_file_content)

    if self.verbose:
      print('Added %s from java kzip' % unit_file_path)

    # Add all files
    for (filename, zip_info) in files.iteritems():
      try:
        with kzip.open(zip_info, 'rU') as f:
          content = f.read()
      except zipfile.BadZipfile as e:
        # Should there be issue with extracting kzip, skip this unit
        print('Error reading generated zip file %s: %s' % (kzip.filename, e))
        continue
      if not self._SetFileHashEntry(filename, filename):
        # File already added
        continue

      path = os.path.join(self.files_directory, filename)
      self.kzip.writestr(path, content)
      if self.verbose:
        print('Added %s from java kzip' % path)

  def _NormalizePath(self, path):
    """Normalize a path.

    For our purposes, "normalized" means relative to the root dir (the one
    containing src/), and passed through os.path.normpath (which eliminates
    double slashes, unnecessary '.' and '..'s, etc.
    """
    return os.path.normpath(os.path.join(self.out_dir, path))

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
        print('Extract source files from %s' % filepaths_fn)

      # We don't want to fail if one of the filepaths doesn't exist. However we
      # keep track of it.
      if not os.path.exists(filepaths_fn):
        print('missing ' + filepaths_fn)
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
      with open(filepaths_fn, 'r') as filepaths_file:
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
      for source in target['sources']:
        # Add the .mojom file itself.
        self._AddDataFile(
            os.path.join(self.root_dir, self.out_dir,
                         ConvertGnPath(source, self.out_dir)))

    for target in self.proto_targets:
      for path in target.GetFiles():
        self._AddDataFile(path)


  def _GenerateUnitFiles(self):
    """Produces the unit files for the index pack.

    A unit file consists of a serialized IndexedCompilation proto. See
    https://github.com/kythe/kythe/blob/master/kythe/proto/analysis.proto for
    the details.
    """

    # Keeps track of the '*.filepaths' files already processed.
    filepaths = set()

    # Add C/C++ compilation units.
    for entry in self.compdb:
      filepaths_fn = os.path.join(entry['directory'],
                                  entry['file'] + '.filepaths')
      if not os.path.exists(filepaths_fn) or filepaths_fn in filepaths:
        continue
      filepaths.add(filepaths_fn)

      self._AddClangUnitFile(entry['file'], entry['directory'],
                             entry['command'], filepaths_fn, self.corpus,
                             build_config=self.build_config)

    # Add Mojom compilation units.
    for target in self.mojom_targets:
      unit_proto = analysis_pb2.CompilationUnit()

      source_files = [
          ConvertPathToForwardSlashes(ConvertGnPath(source, self.out_dir))
          for source in target['sources']
      ]
      unit_proto.source_file.extend(source_files)

      # gn produces an unsubstituted {{response_file_name}} for filelist. We
      # can't work with this, so we remove it and add the source files as a
      # positional argument instead.
      for arg in target['args']:
        if not arg.startswith('--filelist='):
          unit_proto.argument.append(arg)
      unit_proto.argument.extend(source_files)

      unit_proto.v_name.corpus = self.corpus
      unit_proto.v_name.language = 'mojom'
      if self.build_config:
        InjectUnitBuildDetails(unit_proto, self.build_config)

      # Files in a module might import other files in the same module. Don't
      # include the file twice if so.
      imported_files = []
      for imp in target['imported_files']:
        path = os.path.relpath(
            ConvertPathToForwardSlashes(imp),
            os.path.join(self.root_dir, self.out_dir))
        if path not in source_files:
          imported_files.append(path)

      for required_file in source_files + imported_files:
        path = os.path.normpath(
            os.path.join(self.root_dir, self.out_dir, required_file))
        # We don't want to fail completely if the file doesn't exist.
        if path not in self.filehashes:
          print('missing from filehashes %s' % path)
          continue

        required_input = unit_proto.required_input.add()
        required_input.v_name.corpus = self.corpus
        required_input.v_name.path = ConvertPathToForwardSlashes(
            self._NormalizePath(required_file))
        required_input.info.path = ConvertPathToForwardSlashes(required_file)
        required_input.info.digest = self.filehashes[path]

      self._AddUnitFile(unit_proto)

    # add proto compilation units
    for target in self.proto_targets:
      unit = target.GetUnit(self.corpus, self.filehashes, self.build_config)
      if unit:
        self._AddUnitFile(unit)

  def _AddClangUnitFile(self, filename, directory, command, filepaths_fn,
                        corpus, build_config=None):
    """Adds a unit file based on the output of the clang translation_unit tool.

    Args:
      filename: The relative path to the source file from the output directory.
      directory: The output directory (e.g. src/out/Debug).
      command: The command line used to run the compilation.
      filepaths_file: Path to the .filepaths file for this compilation, which
        contains a list of all the required dependency files.
      corpus: The corpus to specify in the unit file.
      build_config: The build config to specify in the unit file, if any.
    """
    # For each compilation unit, generate a CompilationUnit proto.
    unit_proto = analysis_pb2.CompilationUnit()

    if self.verbose:
      print('Generating Translation Unit data for %s' % filename)
      print('Compile command: %s' % command)

    command_list = _ShellSplit(command)
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
      print('No output file path found for %s' % filename)

    if 'clang-cl' in command_list[0]:
      # Convert any args starting with -imsvc to use forward slashes, since
      # this is what Kythe expects.
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

      # Remove any args that may cause errors with the Kythe indexer.
      command_list = [
          arg for arg in command_list if not _IsUnwantedWinArg(arg)
      ]

    # This macro is used to guard Kythe-specific pragmas, so we must define it
    # for Kythe to see them. In particular the kythe_inline_metadata pragma we
    # insert into mojom generated files.
    command_list.append('-DKYTHE_IS_RUNNING=1')

    with open(filepaths_fn, 'r') as filepaths_file:
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
          print('No information about required input file %s' % fname_fullpath)
          continue

        # Handle absolute paths - when normalizing we assume paths are
        # relative to the output directory (e.g. src/out/Debug).
        if os.path.isabs(fname):
          fname = os.path.relpath(fname, directory)

        normalized_fname = self._NormalizePath(fname)
        normalized_fname = ConvertPathToForwardSlashes(normalized_fname)

        required_input = unit_proto.required_input.add()
        _SetVNameForFile(required_input.v_name, normalized_fname, corpus)

        required_input.info.path = ConvertPathToForwardSlashes(fname)
        required_input.info.digest = self.filehashes[fname_fullpath]

    unit_proto.source_file.append(filename)
    unit_proto.working_directory = ConvertPathToForwardSlashes(directory)
    unit_proto.output_key = output_file
    unit_proto.v_name.corpus = _CorpusForFile(filename, corpus)
    unit_proto.v_name.language = 'c++'

    # Add the build config if specified.
    if build_config:
      details = buildinfo_pb2.BuildDetails()
      details.build_config = build_config

      details_any_proto = unit_proto.details.add()
      details_any_proto.Pack(details, 'kythe.io/proto')

    # Disable all warnings with -w so that the indexer can run successfully.
    # The job of the indexer is to index the code, not to verify it. Warnings
    # we actually care about should show up in the compile step.
    unit_proto.argument.extend(command_list)
    unit_proto.argument.append('-w')

    self._AddUnitFile(unit_proto)


  def GenerateIndexPack(self):
    """Generates the index pack.

    An index pack consists of data files (the source and header files) and unit
    files (describing one compilation unit each).
    """
    self._MergeExistingKzips()

    # Generate the source files.
    # This needs to be called first before calling _GenerateUnitFiles()
    self._GenerateDataFiles()

    # Generate the unit files.
    self._GenerateUnitFiles()


def _SetVNameForFile(v_name_proto, filepath, default_corpus):
  """Returns the appropriate VName for a file path.

  Specifically, this checks if the file should be put in a special corpus
  (e.g. the one for the Windows SDK), and if so overrides default_corpus
  and moves the windows path to root.

  Args:
    filepath: A normalized path to a file, using '/' as the path separator.
    default_corpus: The corpus to use if no special corpus is required.
  """
  assert '\\' not in filepath
  v_name_proto.corpus = default_corpus
  v_name_proto.path = filepath
  for prefix, corpus in EXTERNAL_CORPORA:
    if filepath.startswith(prefix + '/'):
      v_name_proto.path = filepath[len(prefix)+1:]
      v_name_proto.root = prefix
      v_name_proto.corpus = corpus
      break


def _CorpusForFile(filepath, default_corpus):
  """Returns the appropriate corpus name for a file path.

  Specifically, this checks if the file should be put in a special corpus
  (e.g. the one for the Windows SDK). If not, returns default_corpus.

  Args:
    filepath: A normalized path to a file, using '/' as the path separator.
    default_corpus: The corpus to use if no special corpus is required.
  """
  assert '\\' not in filepath
  for prefix, corpus in EXTERNAL_CORPORA:
    if filepath.startswith(prefix):
      return corpus
  return default_corpus


def _IsUnwantedWinArg(arg):
  return any(substr in arg for substr in UNWANTED_ARG_SUBSTRINGS_WIN)


def _ReplaceSuffix(string, curr_suffix, new_suffix):
  return string[:len(string) - len(curr_suffix)] + new_suffix


def _MergeFeatureArgs(gn_targets_dict, target_name, target):
  """Adds --enable_feature args from the parser target to the generator target.

  The Mojom toolchain works in two phases, first parsing the file with one tool
  which dumps the AST, then feeding the AST into the bindings generator. The
  Kythe indexer, however, works in one phase, and hence needs some arguments
  from each of these tools. In particular, definitions gated on disabled
  features are removed from the AST directly by the parser tool.

  Args:
    gn_targets_dict: The full parsed JSON dict containing 'gn desc' output for
      the whole compile.
    target_name: The name of the Mojom generator target to merge args into.
    target: gn_targets_dict[target_name]
  """

  parser_target = _ReplaceSuffix(target_name, '__generator', '__parser')
  parser_args = gn_targets_dict[parser_target]['args']
  feature_args = [arg
                  for i in range(len(parser_args) - 1)
                  for arg in parser_args[i:i+2]
                  if parser_args[i] == '--enable_feature']
  return target['args'] + feature_args


def _RemoveFilepathsFiles(root):
  """Removes all .filepaths files within specified root dir."""
  for path, _, files in os.walk(os.path.abspath(root)):
    for filename in fnmatch.filter(files, '*.filepaths'):
      try:
        os.remove(os.path.join(path, filename))
      except OSError as e:
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
                      required=True,
                      help='the kythe corpus to use for the vname')
  parser.add_argument('--path-to-java-kzips',
                      help='path to already generated java kzips which will be '
                      'included in the final index pack')
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

  # Remove the old zip archive (if it exists). This avoids that the new index
  # pack is just added to the old zip archive.
  if os.path.exists(options.path_to_archive_output):
    os.remove(options.path_to_archive_output)

  print('%s: Index generation...' % time.strftime('%X'))
  with closing(
      IndexPack(options.path_to_archive_output, root_dir,
                options.path_to_compdb, options.path_to_gn_targets,
                options.path_to_java_kzips, options.corpus,
                options.build_config, options.out_dir,
                options.verbose)) as index_pack:
    index_pack.GenerateIndexPack()

    if not options.keep_filepaths_files:
      # Clean up the *.filepaths files.
      _RemoveFilepathsFiles(os.path.join(root_dir, 'src'))

  print('%s: Done.' % time.strftime('%X'))
  return 0


if '__main__' == __name__:
  sys.exit(main())
