#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import shutil
import sys
import tempfile
import unittest
import zipfile

BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..')
sys.path.append(os.path.join(BASE_DIR, 'scripts'))
sys.path.append(os.path.join(BASE_DIR, 'site_config'))

from common import archive_utils


DIR_LIST = ['foo',
            os.path.join('fee', 'foo'),
            os.path.join('fee', 'faa'),
            os.path.join('fee', 'fie'),
            os.path.join('foo', 'fee', 'faa')]

TEMP_FILES = ['foo.txt',
              'bar.txt',
              os.path.join('foo', 'buzz.txt'),
              os.path.join('foo', 'bing'),
              os.path.join('fee', 'foo', 'bar'),
              os.path.join('fee', 'faa', 'bar'),
              os.path.join('fee', 'fie', 'fo'),
              os.path.join('foo', 'fee', 'faa', 'boo.txt')]

TEMP_FILES_WITH_WILDCARDS = ['foo.txt',
                             'bar.txt',
                             os.path.join('foo', '*'),
                             os.path.join('fee', '*', 'bar'),
                             os.path.join('fee', '*', 'fo'),
                             os.path.join('foo', 'fee', 'faa', 'boo.txt')]

# Sample FILES.cfg-style contents.
TEST_FILES_CFG = [
  {
    'filename': 'allany.txt',
    'arch': ['32bit', '64bit'],
    'buildtype': ['dev', 'official'],
  },
  {
    'filename': 'subdirectory/allany.txt',
    'arch': ['32bit', '64bit'],
    'buildtype': ['dev', 'official'],
  },
  {
    'filename': 'official64.txt',
    'arch': ['64bit'],
    'buildtype': ['official'],
  },
  {
    'filename': 'dev32.txt',
    'arch': ['32bit'],
    'buildtype': ['dev'],
  },
  {
    'filename': 'archive_allany.txt',
    'arch': ['32bit', '64bit'],
    'buildtype': ['dev', 'official'],
    'archive': 'static_archive.zip',
  },
  {
    'filename': 'subdirectory/archive_allany.txt',
    'arch': ['32bit', '64bit'],
    'buildtype': ['dev', 'official'],
    'archive': 'static_archive.zip',
  },
]


def CreateTestFilesCfg(path):
  files_cfg = os.path.join(path, archive_utils.FILES_FILENAME)
  f = open(files_cfg, 'w')
  f.write('FILES = %s' % str(TEST_FILES_CFG))
  f.close()
  return files_cfg


def CreateFileSetInDir(out_dir, file_list):
  for f in file_list:
    dir_part = os.path.dirname(f)
    if dir_part:
      dir_path = os.path.join(out_dir, dir_part)
      if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    temp_file = open(os.path.join(out_dir, f), 'w')
    temp_file.write('contents')
    temp_file.close()


def BuildTestFilesTree(test_path):
  for temp_file in TEMP_FILES:
    temp_path = os.path.join(test_path, temp_file)
    dir_name = os.path.dirname(temp_path)

    if not os.path.exists(temp_path):
      relative_dir_name = os.path.dirname(temp_file)
      if relative_dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name)
      open(temp_path, 'a')


class ArchiveUtilsTest(unittest.TestCase):

  def setUp(self):
    self.temp_dir = tempfile.mkdtemp()
    self.src_dir = os.path.join(self.temp_dir, 'src')
    self.build_dir = os.path.join(self.temp_dir, 'build')
    self.tool_dir = os.path.join(self.src_dir, 'tools')
    os.makedirs(self.src_dir)
    os.makedirs(self.build_dir)
    os.makedirs(self.tool_dir)

  def tearDown(self):
    shutil.rmtree(self.temp_dir)

  def verifyZipFile(self, zip_dir, zip_file_path, archive_name, expected_files):
    # Extract the files from the archive
    extract_dir = os.path.join(zip_dir, 'extract')
    os.makedirs(extract_dir)
    zip_file = zipfile.ZipFile(zip_file_path)
    # The extractall method is supported from V2.6
    if hasattr(zip_file, 'extractall'):
      zip_file.extractall(extract_dir)  # pylint: disable=E1101
      # Check that all expected files are there
      def FindFiles(arg, dirname, names):
        subdir = dirname[len(arg):].strip(os.path.sep)
        extracted_files.extend([os.path.join(subdir, name) for name in names if
                                os.path.isfile(os.path.join(dirname, name))])
      extracted_files = []
      archive_path = os.path.join(extract_dir, archive_name)
      os.path.walk(archive_path, FindFiles, archive_path)
      self.assertEquals(len(expected_files), len(extracted_files))
      for f in extracted_files:
        self.assertTrue(f in expected_files)
    else:
      test_result = zip_file.testzip()
      self.assertTrue(not test_result)

    zip_file.close()

  def testParseFilesList(self):
    files_cfg = CreateTestFilesCfg(self.temp_dir)
    arch = '64bit'
    buildtype = 'official'
    files_list = archive_utils.ParseFilesList(files_cfg, buildtype, arch)
    # Verify FILES.cfg was parsed correctly.
    for i in TEST_FILES_CFG:
      if arch in i['arch'] and buildtype in i['buildtype']:
        # 'archive' flagged files shouldn't be included in the default parse.
        if i.get('archive'):
          self.assertFalse(i['filename'] in files_list)
        else:
          self.assertTrue(i['filename'] in files_list)
          files_list.remove(i['filename'])
          # No duplicate files.
          self.assertEqual(files_list.count(i['filename']), 0)
    # No unexpected files.
    self.assertEqual(len(files_list), 0)

  def testExtractDirsFromPaths(self):
    path_list = TEMP_FILES[:]
    expected_dir_list = DIR_LIST[:]
    expected_dir_list.sort()

    dir_list = archive_utils.ExtractDirsFromPaths(path_list)
    dir_list.sort()
    self.assertEquals(expected_dir_list, dir_list)

  def testExpandWildcards(self):
    path_list = TEMP_FILES_WITH_WILDCARDS[:]
    expected_path_list = TEMP_FILES[:]
    expected_path_list.sort()

    BuildTestFilesTree(self.temp_dir)

    expanded_path_list = archive_utils.ExpandWildcards(self.temp_dir, path_list)
    expanded_path_list.sort()
    self.assertEquals(expected_path_list, expanded_path_list)

  def testCreateArchive(self):
    files_cfg = CreateTestFilesCfg(self.tool_dir)
    CreateFileSetInDir(self.build_dir, [i['filename'] for i in TEST_FILES_CFG])
    archive_name = 'test'
    arch = '64bit'
    buildtype = 'official'
    files_list = archive_utils.ParseFilesList(files_cfg, buildtype, arch)
    zip_dir, zip_file_path = archive_utils.CreateArchive(
        self.build_dir , self.temp_dir, files_list, archive_name)
    self.assertTrue(zip_dir)
    self.assertTrue(zip_file_path)
    self.assertTrue(os.path.exists(zip_file_path))
    self.verifyZipFile(zip_dir, zip_file_path, archive_name, files_list)

    # Creating the archive twice is wasteful, but shouldn't fail (e.g. due to
    # conflicts with existing zip_dir or zip_file_path). This also tests the
    # condition on the bots where they don't clean up their staging directory
    # between runs.
    zip_dir, zip_file_path = archive_utils.CreateArchive(
        self.build_dir, self.temp_dir, files_list, archive_name)
    self.assertTrue(zip_dir)
    self.assertTrue(zip_file_path)
    self.assertTrue(os.path.exists(zip_file_path))
    self.verifyZipFile(zip_dir, zip_file_path, archive_name, files_list)

  def testCreateEmptyArchive(self):
    files_cfg = CreateTestFilesCfg(self.tool_dir)
    archive_name = 'test_empty'
    arch = '64bit'
    buildtype = 'nosuchtype'
    files_list = archive_utils.ParseFilesList(files_cfg, buildtype, arch)
    zip_dir, zip_file_path = archive_utils.CreateArchive(
        self.build_dir , self.temp_dir, files_list, archive_name)
    self.assertFalse(zip_dir)
    self.assertFalse(zip_file_path)
    self.assertFalse(os.path.exists(zip_file_path))


if __name__ == '__main__':
  # Run with a bit more output.
  suite = unittest.TestLoader().loadTestsFromTestCase(ArchiveUtilsTest)
  unittest.TextTestRunner(verbosity=2).run(suite)
