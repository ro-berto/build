#!/usr/bin/env vpython
# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest

import mock

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,
                os.path.abspath(os.path.join(THIS_DIR, os.pardir, 'resources')))

import repository_util


class RepositoryUtilTest(unittest.TestCase):

  @mock.patch.object(repository_util, 'GetFileRevisions')
  def test_add_git_revisions_to_coverage_files_metadata(
      self, mock_get_file_revisions):
    mock_get_file_revisions.return_value = {
        '//dir1/file1.cc': ('hash1', 1234),
        '//dir2/file2.cc': ('hash2', 5678),
    }

    coverage_files_data = [{'path': '//dir1/file1.cc'}]
    repository_util.AddGitRevisionsToCoverageFilesMetadata(
        coverage_files_data, '/src_path', 'DEPS')
    expected_coverage_files_data = [{
        'path': '//dir1/file1.cc',
        'revision': 'hash1',
        'timestamp': 1234,
    }]
    self.assertListEqual(expected_coverage_files_data, coverage_files_data)


if __name__ == '__main__':
  unittest.main()
