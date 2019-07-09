#!/usr/bin/env vpython
# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import subprocess
import sys
import textwrap
import unittest

import mock

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,
                os.path.abspath(os.path.join(THIS_DIR, os.pardir, 'resources')))

import repository_util


class RepositoryUtilTest(unittest.TestCase):

  @mock.patch('repository_util.os.path.isdir', autospec=True)
  @mock.patch('repository_util.subprocess.check_output', autospec=True)
  def test_get_file_revisions(self, mock_subprocess, mock_is_dir):
    deps_file_content = textwrap.dedent('''
      vars = {
        'chromium_git': 'https://chromium.googlesource.com',
      }

      deps = {
        'src/third_party/repo':
          Var('chromium_git') + '/repo.git' + '@' + 'abcd1234',
      }''')

    def is_dir_side_effect(path):
      path = os.path.normpath(path)
      return path == '/src' or path == '/src/third_party/repo'

    mock_is_dir.side_effect = is_dir_side_effect

    def mock_subprocess_side_effect(commands, cwd):
      cwd = os.path.normpath(cwd)
      if commands[:2] == ['git', 'ls-files']:
        if cwd == '/src':
          return 'file1.cc'
        elif cwd == '/src/third_party/repo':
          return 'file2.cc'
      elif commands[:-1] == ['git', 'log', '-n', '1', '--pretty=format:%H:%ct']:
        if commands[-1] == 'file1.cc' and cwd == '/src':
          return 'file1hash:12345'
        elif commands[-1] == 'file2.cc' and cwd == '/src/third_party/repo':
          return 'file2hash:12345'

      assert False, 'Unexpected subprocess call'

    mock_subprocess.side_effect = mock_subprocess_side_effect

    with mock.patch('repository_util.open',
                    mock.mock_open(read_data=deps_file_content)) as m:
      file_revisions = repository_util.GetFileRevisions(
          '/src', 'DEPS', ['//file1.cc', '//third_party/repo/file2.cc'])

      expected_file_revisions = {
          '//file1.cc': ('file1hash', 12345),
          '//third_party/repo/file2.cc': ('file2hash', 12345)
      }
      self.assertDictEqual(expected_file_revisions, file_revisions)
      m.assert_called_once_with('/src/DEPS', 'r')

  @mock.patch.object(repository_util, 'GetFileRevisions', autospec=True)
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
