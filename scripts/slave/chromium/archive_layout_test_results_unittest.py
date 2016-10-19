#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest

BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
sys.path.append(os.path.join(BASE_DIR, 'scripts'))
sys.path.append(os.path.join(BASE_DIR, 'site_config'))

from slave.chromium import archive_layout_test_results as archive_module


class ArchiveLayoutTestResultsTest(unittest.TestCase):

  def testIsIncludedInZipArchiveFilesCrashLogs(self):
    self.assertTrue(archive_module._IsIncludedInZipArchive('foo-crash-log.txt'))
    self.assertTrue(archive_module._IsIncludedInZipArchive('foo-stack.txt'))

  def testIsIncludedInZipArchiveFilesNonCrashLogFiles(self):
    self.assertFalse(archive_module._IsIncludedInZipArchive('crashlog-foo.txt'))
    self.assertFalse(archive_module._IsIncludedInZipArchive('stack-foo.txt'))

  def testIsIncludedInZipArchiveFilesActualFiles(self):
    self.assertTrue(archive_module._IsIncludedInZipArchive('foo-actual.txt'))
    self.assertTrue(archive_module._IsIncludedInZipArchive('foo-actual.png'))

  def testIsIncludedInZipArchiveFilesActualFilesWrongExtension(self):
    self.assertFalse(archive_module._IsIncludedInZipArchive('foo-actual.jpg'))
    self.assertFalse(archive_module._IsIncludedInZipArchive('foo-actual.html'))

  def testIsIncludedInZipArchiveFilesExpectedFiles(self):
    self.assertTrue(archive_module._IsIncludedInZipArchive('a-expected.txt'))
    self.assertTrue(archive_module._IsIncludedInZipArchive('a-expected.html'))

  def testIsIncludedInZipArchiveFilesDiffFiles(self):
    self.assertTrue(archive_module._IsIncludedInZipArchive('a-diff.png'))
    self.assertTrue(archive_module._IsIncludedInZipArchive('a-diff.txt'))
    self.assertTrue(archive_module._IsIncludedInZipArchive('a-wdiff.txt'))
    self.assertFalse(archive_module._IsIncludedInZipArchive('a-diff.png.foo'))

  def testIsIncludedInZipArchiveFilesOtherNegativeCases(self):
    self.assertFalse(archive_module._IsIncludedInZipArchive('results.html'))
    self.assertFalse(archive_module._IsIncludedInZipArchive('my-test.html'))

  def testIsIncludedInZipArchiveFilesJson(self):
    self.assertTrue(archive_module._IsIncludedInZipArchive('results.json'))


if __name__ == '__main__':
  unittest.main()
