#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import shutil
import sys
import tempfile
import unittest

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

  def tearDown(self):
    shutil.rmtree(self.temp_dir)

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


if __name__ == '__main__':
  # Run with a bit more output.
  suite = unittest.TestLoader().loadTestsFromTestCase(ArchiveUtilsTest)
  unittest.TextTestRunner(verbosity=2).run(suite)
