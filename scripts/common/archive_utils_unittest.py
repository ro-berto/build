#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
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

# Sample FILES.cfg-style contents.
TEST_FILES_CFG = [
  {
    'filename': 'allany.txt',
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
]


def CreateTestFilesCfg(path):
  files_cfg = os.path.join(path, archive_utils.FILES_FILENAME)
  f = open(files_cfg, 'w')
  f.write("FILES = %s" % str(TEST_FILES_CFG))
  f.close()
  return files_cfg


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
        self.assertTrue(i['filename'] in files_list)
        files_list.remove(i['filename'])
        # No duplicate files.
        self.assertEqual(files_list.count(i['filename']), 0)
    # No unexpected files.
    self.assertEqual(len(files_list), 0)


if __name__ == '__main__':
  # Run with a bit more output.
  suite = unittest.TestLoader().loadTestsFromTestCase(ArchiveUtilsTest)
  unittest.TextTestRunner(verbosity=2).run(suite)
