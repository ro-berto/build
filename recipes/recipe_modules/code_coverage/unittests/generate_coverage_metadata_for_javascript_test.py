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


if __name__ == '__main__':
  unittest.main()
