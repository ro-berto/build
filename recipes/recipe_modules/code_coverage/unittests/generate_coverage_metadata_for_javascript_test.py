#!/usr/bin/env vpython
# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest

import mock

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,
                os.path.abspath(os.path.join(THIS_DIR, os.pardir, 'resources')))

import generate_coverage_metadata_for_javascript as generator


class GenerateCoverageMetadataForJavaScriptTest(unittest.TestCase):

  @mock.patch.object(os, 'listdir')
  def test_get_json_files_ignores_everything_else(self, mock_listdir):
    mock_input_dir_listdir = [
        '/b/some/path/browser_tests_javascript.json',
        '/b/some/path/unexpected_file.txt',
        '/b/some/path/tests',
        '/b/some/path/scripts',
    ]
    mock_listdir.return_value = mock_input_dir_listdir

    expected_output = [
        '/b/some/path/browser_tests_javascript.json',
    ]
    actual_output = generator.get_json_coverage_files('/b/some/path')
    self.assertListEqual(expected_output, actual_output)

  @mock.patch.object(os.path, 'exists')
  def test_get_source_files_returns_relative_paths(self, mock_exists):
    mock_input_coverage_info = '{ \
      "//relative/path/to/file/a.js": [{"end": 100, "count": 2}], \
      "//relative/path/to/file/b.js": [{"end": 200, "count": 1}] \
    }'

    mock_exists.side_effect = [True, True]

    actual_output = []
    with mock.patch.object(
        generator,
        'open',
        mock.mock_open(read_data=mock_input_coverage_info),
        create=True):
      actual_output = generator.get_coverage_data_and_paths(
          '/b/some/path/src', '/b/some/path/coverage_data.json')

    expected_output = {
        '/b/some/path/src/relative/path/to/file/a.js': [{
            'end': 100,
            'count': 2
        }],
        '/b/some/path/src/relative/path/to/file/b.js': [{
            'end': 200,
            'count': 1
        }]
    }

    self.assertEqual(actual_output, expected_output)

  @mock.patch.object(os.path, 'exists')
  def test_get_source_files_nonexistant_path_fails(self, mock_exists):
    mock_input_coverage_info = '{ \
      "//relative/path/to/file/a.js": [], \
      "//relative/path/to/file/b.js": [] \
    }'

    # Return False for the first absolute path indicating
    # the file /b/some/path/src/relative/path/to/file/a.js
    # does not exist.
    mock_exists.side_effect = [False, True]

    with mock.patch.object(
        generator,
        'open',
        mock.mock_open(read_data=mock_input_coverage_info),
        create=True):
      with self.assertRaises(Exception):
        generator.get_coverage_data_and_paths(
            '/b/some/path/src', '/b/some/path/coverage_data.json')


if __name__ == '__main__':
  unittest.main()
