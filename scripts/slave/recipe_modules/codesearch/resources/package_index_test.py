#!/usr/bin/env vpython
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for package_index.py."""

from __future__ import absolute_import

import hashlib
import json
import os
import shutil
import tempfile
import unittest
import zipfile

import package_index

# Test values for corpus, build config, and out dir
CORPUS = 'chromium-test'
BUILD_CONFIG = 'linux'
OUT_DIR = 'src/out/Debug'

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_DATA_DIR = os.path.join(SCRIPT_DIR, 'package_index_testdata')
TEST_DATA_INPUT_DIR = os.path.join(TEST_DATA_DIR, 'input')

class PackageIndexTest(unittest.TestCase):

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

    # Create a path for the archive to be written to.
    with tempfile.NamedTemporaryFile(
        suffix='.kzip', delete=False) as archive_file:
      self.archive_path = archive_file.name

    self.index_pack = package_index.IndexPack(
        self.archive_path,
        TEST_DATA_INPUT_DIR,
        os.path.join(self.build_dir, 'compile_commands.json'),
        os.path.join(self.build_dir, 'gn_targets.json'),
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
        os.path.join(self.unpacked_index_dir, 'kzip', 'units')))

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
    """Parses all JSON files in a dir and returns them in a dict.

    Assumes that the dicts contain entries accessible at
    dict['unit']['v_name']['corpus'] and dict['unit']['source_file'][0], which
    are used for keying.
    """
    unit_dicts = {}
    for filename in os.listdir(units_dir):
      with open(os.path.join(units_dir, filename), 'r') as unit_file:
        unit_dict = json.load(unit_file)
        key = (unit_dict['unit']['v_name']['corpus'],
               unit_dict['unit']['source_file'][0])
        unit_dicts[key] = unit_dict
    return unit_dicts

  def _CheckUnitFilesMatch(self, out_dir, golden_dir):
    """Checks that the JSON files in out_dir and golden_dir are equivalent.

    Doesn't care about filenames or formatting of the JSON files; only that the
    dicts are equivalent after parsing.

    Assumes that the dicts contain entries accessible at
    dict['unit']['v_name']['corpus'] and dict['unit']['source_file'][0], which
    are used for keying.
    """
    actual_files = os.listdir(out_dir)
    golden_files = os.listdir(golden_dir)
    self.assertEqual(len(golden_files), len(actual_files))

    actual_dicts = self._GetDictOfUnitFilesInDir(out_dir)
    golden_dicts = self._GetDictOfUnitFilesInDir(golden_dir)
    for key, unit_dict in actual_dicts.items():
      self.assertIn(key, golden_dicts.keys())
      self.assertEqual(golden_dicts[key], unit_dict)

  def testGenerateDataFiles(self):
    self._CheckFilesMatchExactly(
        out_dir=os.path.join(self.unpacked_index_dir, 'kzip', 'files'),
        golden_dir=os.path.join(TEST_DATA_DIR, 'expected_files'))

  def testGenerateUnitFiles(self):
    self._CheckUnitFilesMatch(
        out_dir=os.path.join(self.unpacked_index_dir, 'kzip', 'units'),
        golden_dir=os.path.join(TEST_DATA_DIR, 'expected_units'))

  def testGenerateUnitFilesWindows(self):
    # Recreate the index pack using a different compilation database.
    self.index_pack = package_index.IndexPack(
        self.archive_path,
        TEST_DATA_INPUT_DIR,
        os.path.join(self.build_dir, 'compile_commands_win.json'),
        os.path.join(self.build_dir, 'gn_targets.json'),
        corpus=CORPUS,
        build_config=BUILD_CONFIG,
        out_dir=OUT_DIR,
        verbose=True)
    self.index_pack.GenerateIndexPack()
    self.index_pack.close()

    shutil.rmtree(self.unpacked_index_dir)
    self.unpacked_index_dir = tempfile.mkdtemp()
    z = zipfile.ZipFile(self.archive_path, 'r')
    z.extractall(self.unpacked_index_dir)
    z.close()

    self._CheckUnitFilesMatch(
        out_dir=os.path.join(self.unpacked_index_dir, 'kzip', 'units'),
        golden_dir=os.path.join(TEST_DATA_DIR, 'expected_units_win'))

  def testCreateArchive(self):
    # Verify the structure of the archive. It should be as follows:
    # kzip/              # Any valid non-empty directory name
    #   units/
    #     abcd1234       # Compilation unit (name is SHA256 of content)
    #     ...
    #   files/
    #     1a2b4c4d       # File contents
    #     ...
    self.assertTrue(os.path.exists(self.archive_path))
    with zipfile.ZipFile(self.archive_path, 'r') as archive:
      zipped_filenames = archive.namelist()

    root = 'kzip'
    self.assertIn(root + os.path.sep, zipped_filenames);

    # Verify that the units/ dir has its own entry.
    self.assertIn(os.path.join(root, 'units', ''), zipped_filenames)

    # Rather than hardcode the SHA256 of the unit files here, we simply verify
    # that at least one exists and that they are all present in the zip.
    units_dir = os.path.join(self.unpacked_index_dir, 'kzip', 'units')
    unit_files = os.listdir(units_dir)
    self.assertNotEqual(0, len(unit_files))
    for unit_file_name in unit_files:
      self.assertIn(os.path.join(root, 'units', unit_file_name),
                    zipped_filenames)

    # Verify that the files/ dir has its own entry.
    self.assertIn(os.path.join(root, 'files', ''), zipped_filenames)

    # Verify that the kzip contains all expected data files.
    data_filenames = [os.path.basename(path)
                      for path in zipped_filenames
                      if 'files' in path
                      and os.path.basename(path) != '']
    golden_filenames = os.listdir(os.path.join(TEST_DATA_DIR, 'expected_files'))
    self.assertEqual(set(golden_filenames), set(data_filenames))

if __name__ == '__main__':
  unittest.main()
