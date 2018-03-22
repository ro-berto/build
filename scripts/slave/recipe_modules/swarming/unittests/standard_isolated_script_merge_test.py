#!/usr/bin/env vpython
# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import itertools
import json
import os
import shutil
import sys
import tempfile
import unittest

import mock

import common_merge_script_tests

THIS_DIR = os.path.dirname(__file__)

sys.path.insert(
    0, os.path.abspath(os.path.join(THIS_DIR, '..', '..', '..', 'unittests')))
import test_env

sys.path.insert(
    0, os.path.abspath(os.path.join(THIS_DIR, '..', 'resources')))
import standard_isolated_script_merge


class StandardIsolatedScriptMergeTest(unittest.TestCase):

  def setUp(self):
    self.merge_test_results_args = []
    def mock_merge_test_results(results_list):
      self.merge_test_results_args.append(results_list)
      return {
        'foo': [
          'bar',
          'baz',
        ],
      }

    m = mock.patch(
      'standard_isolated_script_merge.results_merger.merge_test_results',
      side_effect=mock_merge_test_results)
    m.start()
    self.addCleanup(m.stop)

    self.temp_dir = tempfile.mkdtemp()

  def tearDown(self):
    shutil.rmtree(self.temp_dir)
    super(StandardIsolatedScriptMergeTest, self).tearDown()

  def test_simple(self):

    results = [
      {
        'result0': ['bar', 'baz'],
      },
      {
        'result1': {'foo': 'bar'}
      }
    ]
    json_files = [
      os.path.join(self.temp_dir, 'input0.json'),
      os.path.join(self.temp_dir, 'input1.json')
    ]

    for result, json_file in itertools.izip(results, json_files):
      with open(json_file, 'w') as f:
        json.dump(result, f)

    output_json_file = os.path.join(self.temp_dir, 'output.json')
    exit_code = standard_isolated_script_merge.StandardIsolatedScriptMerge(
        output_json_file, json_files)

    self.assertEquals(0, exit_code)
    self.assertEquals(
      [
        [
          {
            'result0': [
              'bar', 'baz',
            ],
          },
          {
            'result1': {
              'foo': 'bar',
            },
          }
        ],
      ],
      self.merge_test_results_args)

  def test_no_jsons(self):
    json_files = []
    output_json_file = os.path.join(self.temp_dir, 'output.json')
    exit_code = standard_isolated_script_merge.StandardIsolatedScriptMerge(
        output_json_file, json_files)

    self.assertEquals(0, exit_code)
    self.assertEquals([[]], self.merge_test_results_args)


class CommandLineTest(common_merge_script_tests.CommandLineTest):

  def __init__(self, methodName='runTest'):
    super(CommandLineTest, self).__init__(methodName, standard_isolated_script_merge)


if __name__ == '__main__':
  unittest.main()
