#!/usr/bin/env vpython
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for package_index.py."""

from __future__ import absolute_import

import hashlib
import mock
import os
import shutil
import sys
import tempfile
import time
import unittest
import zipfile

import google.protobuf.text_format
from kythe.proto import analysis_pb2

import package_index

# Test values for corpus, build config, and out dir
CORPUS = 'chromium-test'
BUILD_CONFIG = 'linux'
OUT_DIR = 'src/out/Debug'

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_DATA_DIR = os.path.join(SCRIPT_DIR, 'package_index_testdata')
TEST_DATA_INPUT_DIR = os.path.join(TEST_DATA_DIR, 'input.expected')


class FunctionTest(unittest.TestCase):
  """Test functions in package_index"""

  def testInjectUtilBuildDetails(self):
    unit = analysis_pb2.CompilationUnit()
    package_index.InjectUnitBuildDetails(unit, 'linux')
    self.assertEqual(1, len(unit.details))
    self.assertTrue('linux' in str(unit.details))

    package_index.InjectUnitBuildDetails(unit, 'win')
    self.assertTrue('linux' not in str(unit.details))
    self.assertTrue('win' in str(unit.details))

  def testInjectUtilBuildDetailsMultipleDetails(self):
    """This tests that build details doesn't override non BuildDetails detail"""
    unit = analysis_pb2.CompilationUnit()
    unit.details.add()
    package_index.InjectUnitBuildDetails(unit, 'linux')
    self.assertEqual(2, len(unit.details))

  def testConvertGnPath(self):
    self.assertEqual('../../foo.ext',
                     package_index.ConvertGnPath('//foo.ext', 'src/out/debug'))
    self.assertEqual('../../../../foo.ext',
                     package_index.ConvertGnPath('//foo.ext', 'src/a/b/c/d'))

  def testImport(self):
    src_dir = os.path.join(TEST_DATA_INPUT_DIR, 'src')

    # Expectation: test.mojom includes test2.mojom.
    path = os.path.join(src_dir, 'test.mojom')
    files = package_index.FindImports(package_index.MOJOM_IMPORT_RE, path,
                                      [src_dir])
    self.assertEqual(set([os.path.join(src_dir, 'test2.mojom')]), files)

    # File can't be found, ignore it.
    files = package_index.FindImports(package_index.MOJOM_IMPORT_RE, path,
                                      [TEST_DATA_INPUT_DIR])
    self.assertEqual(set(), files)

    # Expectation: test2.mojom has no imports.
    path = os.path.join(src_dir, 'test2.mojom')
    files = package_index.FindImports(package_index.MOJOM_IMPORT_RE, path,
                                      [src_dir])
    self.assertEqual(set(), files)

    # Expectation: main.proto has sub.proto and subsub.proto import.
    path = os.path.join(src_dir, 'main.proto')
    files = package_index.FindImports(package_index.PROTO_IMPORT_RE, path,
                                      [src_dir])
    self.assertEqual(
        set([
            os.path.join(src_dir, 'sub.proto'),
            os.path.join(src_dir, 'subsub.proto')
        ]), files)


class ProtoTargetTest(unittest.TestCase):
  """Test ProtoTarget class"""

  def ImportMockGen(self, expected_regex, expected_paths, import_mapping):

    def InnerFunc(regex, file_path, import_paths):
      self.assertEqual(expected_regex, regex)
      self.assertEqual(expected_paths, import_paths)
      self.assertIn(file_path, import_mapping)
      return import_mapping[file_path]

    return InnerFunc

  @mock.patch('package_index.FindImports')
  def testNoProtoInDir(self, findImportsMock):
    findImportsMock.side_effect = self.ImportMockGen(
        package_index.PROTO_IMPORT_RE, ['/foo/src/out/debug'], {
            '/foo/src/orig.proto': set(['/foo/src/out/debug/baz.proto']),
            '/foo/src/out/debug/baz.proto': set(),
        })

    pt = package_index.ProtoTarget({
        'sources': ['//orig.proto']
    }, '/foo', 'src/out/debug')

    expected_result = set(
        ['/foo/src/orig.proto', '/foo/src/out/debug/baz.proto'])
    self.assertEqual(expected_result, pt.GetFiles())
    self.assertEqual(2, findImportsMock.call_count)

  @mock.patch('package_index.FindImports')
  def testProtoInDir(self, findImportsMock):
    findImportsMock.side_effect = self.ImportMockGen(
        package_index.PROTO_IMPORT_RE, ['/foo/src', '/abspath'], {
            '/foo/src/orig.proto': set(['/abspath/baz.proto']),
            '/foo/src/orig2.proto': set(),
            '/abspath/baz.proto': set(),
        })

    # Last proto-in-dir should be discarded
    args = [
        '--proto-in-dir', '../..', 'x', '--import-dir=/abspath',
        '--proto-in-dir'
    ]
    pt = package_index.ProtoTarget({
        'sources': ['//orig.proto', '//orig2.proto'],
        'args': args
    }, '/foo', 'src/out/debug')

    expected_result = set(
        ['/foo/src/orig.proto', '/foo/src/orig2.proto', '/abspath/baz.proto'])
    self.assertEqual(expected_result, pt.GetFiles())
    self.assertEqual(3, findImportsMock.call_count)

    # Test getting compilation unit
    filehashes = {
        '/foo/src/orig.proto': '1',
        '/foo/src/orig2.proto': '2',
        '/abspath/baz.proto': '3',
    }
    unit_proto = pt.GetUnit('corpusname', filehashes, 'build_config')
    self.assertIsNotNone(unit_proto)
    self.assertEqual(['../../orig.proto', '../../orig2.proto'],
                     unit_proto.source_file)
    self.assertEqual('protobuf', unit_proto.v_name.language)
    self.assertEqual('corpusname', unit_proto.v_name.corpus)
    self.assertEqual(1, len(unit_proto.details))
    self.assertEqual(3, len(unit_proto.required_input))
    # Expect no new calls, the results should be cached
    self.assertEqual(3, findImportsMock.call_count)

  @mock.patch('package_index.FindImports')
  def testRecusiveImport(self, findImportsMock):
    findImportsMock.side_effect = self.ImportMockGen(
        package_index.PROTO_IMPORT_RE, ['/foo/src'], {
            '/foo/src/orig.proto': set(['/foo/src/import.proto']),
            '/foo/src/import.proto': set(['/foo/src/import2.proto']),
            '/foo/src/import2.proto': set(),
        })

    # Last proto-in-dir should be discarded
    args = ['--proto-in-dir', '../..']
    pt = package_index.ProtoTarget({
        'sources': ['//orig.proto', '//import.proto'],
        'args': args
    }, '/foo', 'src/out/debug')

    expected_result = set([
        '/foo/src/orig.proto', '/foo/src/import.proto', '/foo/src/import2.proto'
    ])
    self.assertEqual(expected_result, pt.GetFiles())
    self.assertEqual(3, findImportsMock.call_count)

    # Test getting compilation unit
    filehashes = {
        '/foo/src/orig.proto': '1',
        '/foo/src/import.proto': '2',
        '/foo/src/import2.proto': '3',
    }
    unit_proto = pt.GetUnit('corpusname', filehashes, 'build_config')
    self.assertIsNotNone(unit_proto)
    # Only explicitly imported source files should be here, sorted
    self.assertEqual(['../../import.proto', '../../orig.proto'],
                     unit_proto.source_file)
    self.assertEqual('protobuf', unit_proto.v_name.language)
    self.assertEqual('corpusname', unit_proto.v_name.corpus)
    self.assertEqual(1, len(unit_proto.details))
    self.assertEqual(3, len(unit_proto.required_input))

  @mock.patch('package_index.FindImports')
  def testProtoMissingFile(self, findImportsMock):
    findImportsMock.side_effect = self.ImportMockGen(
        package_index.PROTO_IMPORT_RE, ['/foo/src/out/debug'], {
            '/foo/src/orig.proto': set(),
        })

    pt = package_index.ProtoTarget({
        'sources': ['//orig.proto']
    }, '/foo', 'src/out/debug')

    expected_result = set(['/foo/src/orig.proto'])
    self.assertEqual(expected_result, pt.GetFiles())
    unit_proto = pt.GetUnit('corpusname', {}, 'build_config')
    self.assertIsNone(unit_proto)
    self.assertEqual(1, findImportsMock.call_count)


class IndexPackBootstrap(unittest.TestCase):
  """IndexPackBootstrap is "abstract" class used by other test cases classes"""

  def setUp(self):
    self.maxDiff = None

    # Since our test compdb has a relative path in it, we need to ensure the
    # working directory is the directory that contains this test file, and save
    # it so we can change back after the test.
    self.saved_cwd = os.getcwd()
    os.chdir(SCRIPT_DIR)

    # Our test data emulates the chromium build directory setup: a root dir
    # named "src" which contains the code in subdirectories, along with an
    # "out/Debug" build directory which all the compilation DB
    # entries are relative to.
    self.build_dir = os.path.join(TEST_DATA_INPUT_DIR, OUT_DIR)

    # Set new.kzip to be modified the last.
    today = time.time()
    # Set to yesterday as some operating systems may have 1 day resolution.
    yesterday = today - 86400
    os.utime(os.path.join(self.build_dir, 'kzip', 'new.kzip'), (today, today))
    os.utime(
        os.path.join(self.build_dir, 'kzip', 'old_duplicate.kzip'),
        (yesterday, yesterday))

    # Create a path for the archive to be written to.
    with tempfile.NamedTemporaryFile(
        suffix='.kzip', delete=False) as archive_file:
      self.archive_path = archive_file.name


class IndexPackInvalidParametersTest(IndexPackBootstrap):
  """IndexPackInvalidParametersTest tests constructor failures"""

  def testInvalidKzips(self):
    with self.assertRaises(Exception):
      package_index.IndexPack(
          self.archive_path,
          TEST_DATA_INPUT_DIR,
          os.path.join(self.build_dir, 'compile_commands.json'),
          os.path.join(self.build_dir, 'gn_targets.json'),
          os.path.join(self.build_dir, 'invalid_kzip_path'),
          corpus=CORPUS,
          build_config=BUILD_CONFIG,
          out_dir=OUT_DIR,
          verbose=True)


class IndexPackTest(IndexPackBootstrap):
  """IndexPackTest contains integration tests that should cover entire
  package_index
  """

  def setUp(self):
    super(IndexPackTest, self).setUp()

    self.index_pack = package_index.IndexPack(
        self.archive_path,
        TEST_DATA_INPUT_DIR,
        os.path.join(self.build_dir, 'compile_commands.json'),
        os.path.join(self.build_dir, 'gn_targets.json'),
        os.path.join(self.build_dir, 'kzip'),
        corpus=CORPUS,
        build_config=BUILD_CONFIG,
        out_dir=OUT_DIR,
        verbose=True)
    self.index_pack.GenerateIndexPack()
    self.index_pack.close()

    self.unpacked_index_dir = tempfile.mkdtemp()
    z = zipfile.ZipFile(self.archive_path, 'r')
    z.extractall(self.unpacked_index_dir)
    z.close()

    self.assertTrue(os.path.exists(
        os.path.join(self.unpacked_index_dir, 'kzip', 'files')))
    self.assertTrue(os.path.exists(
        os.path.join(self.unpacked_index_dir, 'kzip', 'pbunits')))

  def tearDown(self):
    if os.path.exists(self.archive_path):
      os.remove(self.archive_path)
    shutil.rmtree(self.unpacked_index_dir)
    os.chdir(self.saved_cwd)

  def _CheckFilesMatchExactly(self, out_dir, golden_dir):
    """Checks the files in out_dir are identical to the files in golden_dir."""
    # Check the filenames match.
    actual_files = os.listdir(out_dir)
    golden_files = os.listdir(golden_dir)
    self.assertEqual(set(golden_files), set(actual_files))

    for filename in actual_files:
      with open(os.path.join(out_dir, filename), 'r') as actual_file:
        with open(os.path.join(golden_dir, filename), 'r') as golden_file:
          self.assertEqual(golden_file.read(), actual_file.read())

  def _GetDictOfUnitFilesInDir(self, units_dir):
    """Parses all unit files in a dir and returns them in a dict.

    Assumes that the files contain text or wire format
    kythe.proto.IndexedCompilation protos which have fields unit.v_name.corpus
    and unit.source_file[0] set, as they are used for keying.
    """
    unit_protos = {}
    for filename in os.listdir(units_dir):
      with open(os.path.join(units_dir, filename), 'rb') as unit_file:
        unit_file_data = unit_file.read()

        unit_proto = analysis_pb2.IndexedCompilation()
        unit_proto.ParseFromString(unit_file_data)

        key = (unit_proto.unit.v_name.corpus, unit_proto.unit.source_file[0])
        unit_protos[key] = str(unit_proto).splitlines()
    return unit_protos

  def _GetDictOfGoldenUnitFilesInDir(self, units_dir):
    unit_protos = {}
    for filename in os.listdir(units_dir):
      with open(os.path.join(units_dir, filename), 'r') as unit_file:
        unit_protos[filename] = unit_file.read().splitlines()
    return unit_protos

  def _CheckUnitFilesMatch(self, out_dir, golden_dir):
    """Checks that the proto files in out_dir and golden_dir are equivalent.

    Doesn't care about filenames, only that the contained protos are equivalent.

    Assumes that the protos have fields unit.v_name.corpus and
    unit.source_file[0] set, as they are used for keying.
    """
    actual_files = os.listdir(out_dir)
    golden_files = os.listdir(golden_dir)
    self.assertEqual(len(golden_files), len(actual_files))

    actual_dicts = self._GetDictOfUnitFilesInDir(out_dir)
    golden_dicts = self._GetDictOfGoldenUnitFilesInDir(golden_dir)
    for key, unit_dict in actual_dicts.items():
      golden_key = os.path.basename(key[1])
      self.assertEqual(golden_dicts[golden_key], unit_dict)

  def testGenerateDataFiles(self):
    self._CheckFilesMatchExactly(
        out_dir=os.path.join(self.unpacked_index_dir, 'kzip', 'files'),
        golden_dir=os.path.join(TEST_DATA_DIR, 'files.expected'))

  def testGenerateUnitFiles(self):
    # Do not run the linux tests pbunits on windows, windows shell escaping is
    # just too broken to trust the unit test results.
    if sys.platform != 'win32':
      self._CheckUnitFilesMatch(
          out_dir=os.path.join(self.unpacked_index_dir, 'kzip', 'pbunits'),
          golden_dir=os.path.join(TEST_DATA_DIR, 'units.expected'))

  def testGenerateUnitFilesWindows(self):
    # Since most development is done in linux, windows tests are runnable
    # in both linux and windows. However, win32 treats \ on the command line
    # very differently, so fix the commands file so it can be tested in windows.
    # * windows treats \'s differently than shlex.  (see
    #   https://docs.microsoft.com/en-us/windows/win32/api/shellapi/
    #   nf-shellapi-commandlinetoargvw#remarks) so, we need to halve the
    #   \'s for windows runs (assuming no in/out of quotes)
    # * Json needs \ escaping, so replacing 2 \'s with 1 \ requires replacing
    #   4 \'s with 2 \'s.
    win32_fix_dir = ""
    compile_commands_file = os.path.join(self.build_dir,
                                         'compile_commands_win.json')
    if sys.platform == 'win32':
      win32_fix_dir = tempfile.mkdtemp()
      with open(compile_commands_file) as commands:
        win32_fix_dir = tempfile.mkdtemp()
        compile_commands_file = os.path.join(win32_fix_dir,
                                             'compile_commands_win.json')
        with open(compile_commands_file, 'w') as new_commands:
          for line in commands:
            new_commands.write(line.replace(r'\\\\', r'\\'))

    # Recreate the index pack using a different compilation database.
    self.index_pack = package_index.IndexPack(
        self.archive_path,
        TEST_DATA_INPUT_DIR,
        compile_commands_file,
        os.path.join(self.build_dir, 'gn_targets.json'),
        os.path.join(self.build_dir, 'kzip'),
        corpus=CORPUS,
        build_config='win',
        out_dir=OUT_DIR,
        verbose=True)
    self.index_pack.GenerateIndexPack()
    self.index_pack.close()

    if win32_fix_dir:
      shutil.rmtree(win32_fix_dir)
    shutil.rmtree(self.unpacked_index_dir)
    self.unpacked_index_dir = tempfile.mkdtemp()
    z = zipfile.ZipFile(self.archive_path, 'r')
    z.extractall(self.unpacked_index_dir)
    z.close()

    self._CheckUnitFilesMatch(
        out_dir=os.path.join(self.unpacked_index_dir, 'kzip', 'pbunits'),
        golden_dir=os.path.join(TEST_DATA_DIR, 'units_win.expected'))

  def testCreateArchive(self):
    # Verify the structure of the archive. It should be as follows:
    # kzip/              # Any valid non-empty directory name
    #   pbunits/
    #     abcd1234       # Compilation unit (name is SHA256 of content)
    #     ...
    #   files/
    #     1a2b4c4d       # File contents
    #     ...
    self.assertTrue(os.path.exists(self.archive_path))
    with zipfile.ZipFile(self.archive_path, 'r') as archive:
      zipped_filenames = archive.namelist()

    # kzips use unix path separators, not the native os separator
    root = 'kzip'
    self.assertIn(root + '/', zipped_filenames)

    # Verify that the units/ dir has its own entry.
    self.assertIn('/'.join([root, 'pbunits', '']), zipped_filenames)

    # Rather than hardcode the SHA256 of the unit files here, we simply verify
    # that at least one exists and that they are all present in the zip.
    units_dir = '/'.join([self.unpacked_index_dir, 'kzip', 'pbunits'])
    unit_files = os.listdir(units_dir)
    self.assertNotEqual(0, len(unit_files))
    for unit_file_name in unit_files:
      self.assertIn('/'.join([root, 'pbunits', unit_file_name]),
                    zipped_filenames)

    # Verify that the files/ dir has its own entry.
    self.assertIn('/'.join([root, 'files', '']), zipped_filenames)

    # Verify that the kzip contains all expected data files.
    data_filenames = [os.path.basename(path)
                      for path in zipped_filenames
                      if 'files' in path
                      and os.path.basename(path) != '']
    golden_filenames = os.listdir(os.path.join(TEST_DATA_DIR, 'files.expected'))
    self.assertEqual(set(golden_filenames), set(data_filenames))

if __name__ == '__main__':
  unittest.main()
