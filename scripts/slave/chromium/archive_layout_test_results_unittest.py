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

from slave.chromium import archive_layout_test_results


class ArchiveLayoutTestResultsTest(unittest.TestCase):

  def test_IsActualResultFile(self):
    self.assertTrue(archive_layout_test_results._IsActualResultFile(
        'foo-crash-log.txt'))
    self.assertTrue(archive_layout_test_results._IsActualResultFile(
        'foo-stack.txt'))

    self.assertFalse(archive_layout_test_results._IsActualResultFile(
        'crash-logging-foo.txt'))
    self.assertFalse(archive_layout_test_results._IsActualResultFile(
        'stack-foo.txt'))

    self.assertTrue(archive_layout_test_results._IsActualResultFile(
        'foo-actual.txt'))
    self.assertTrue(archive_layout_test_results._IsActualResultFile(
        'foo-actual.png'))

    self.assertFalse(archive_layout_test_results._IsActualResultFile(
        'foo-actual.jpg'))
    self.assertFalse(archive_layout_test_results._IsActualResultFile(
        'foo-actual.html'))

  def test_IsDiffFile(self):
    self.assertTrue(archive_layout_test_results._IsDiffFile('a-diff.png'))
    self.assertTrue(archive_layout_test_results._IsDiffFile('a-diff.txt'))
    self.assertTrue(archive_layout_test_results._IsDiffFile('a-wdiff.txt'))
    self.assertTrue(archive_layout_test_results._IsDiffFile('a-expected.txt'))
    self.assertTrue(archive_layout_test_results._IsDiffFile('a-expected.html'))

    self.assertFalse(archive_layout_test_results._IsDiffFile('a-diff.png.foo'))
    self.assertFalse(archive_layout_test_results._IsDiffFile('a-diff.png.foo'))
    self.assertFalse(archive_layout_test_results._IsDiffFile('foo-actual.html'))
    self.assertFalse(archive_layout_test_results._IsDiffFile('results.html'))

if __name__ == '__main__':
  unittest.main()
