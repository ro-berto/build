#!/usr/bin/env python
# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for upload_test_results.py."""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(
      os.path.dirname(__file__), '..', '..', '..', '..'))
import common.env
common.env.Install()
import mock

import upload_test_results


class UploadTestResultsTest(unittest.TestCase):

  def setUp(self):
    pass

  def test_no_test_data(self):
    results = upload_test_results.get_results_map_from_json(
        json.dumps({}))
    self.assertEquals({}, results)

  def test_multiple_results(self):
    contents = {
        'per_iteration_data': [{
            'Fake.Test': [
                {'status': 'FAILURE', 'elapsed_time_ms': 1000},
                {'status': 'SUCCESS', 'elapsed_time_ms': 0},
            ],
        }],
    }
    results = upload_test_results.get_results_map_from_json(
        json.dumps(contents))
    self.assertEquals('FAIL', results['Fake.Test'][0].status)
    self.assertEquals(1, results['Fake.Test'][0].test_run_time)
    self.assertEquals('PASS', results['Fake.Test'][1].status)
    self.assertEquals(0, results['Fake.Test'][1].test_run_time)

  def test_bad_status(self):
    contents = {
        'per_iteration_data': [{
            'Fake.Test': [
                {'status': 'XXX', 'elapsed_time_ms': 1000},
            ],
        }],
    }
    results = upload_test_results.get_results_map_from_json(
        json.dumps(contents))
    self.assertEquals('UNKNOWN', results['Fake.Test'][0].status)
    self.assertEquals(1, results['Fake.Test'][0].test_run_time)

  def test_skipped(self):
    contents = {
        'disabled_tests': [
            'Disabled.Test',
        ],
        'per_iteration_data': [{
            'Skipped.Test': [
                {'status': 'SKIPPED', 'elapsed_time_ms': 0},
            ],
        }],
    }
    results = upload_test_results.get_results_map_from_json(
        json.dumps(contents))
    self.assertEquals(results['Disabled.Test'][0].DISABLED,
                      results['Disabled.Test'][0].modifier)
    self.assertEquals(results['Disabled.Test'][0].DISABLED,
                      results['Skipped.Test'][0].modifier)

  @mock.patch('test_results_uploader.upload_test_results')
  def test_main(self, uploader_mock):
    contents = {
        'per_iteration_data': [{
            'Fake.Test': [
                {'status': 'XXX', 'elapsed_time_ms': 1000},
            ],
        }],
    }
    result_directory = tempfile.mkdtemp()
    input_json_file_path = os.path.join(result_directory, 'results.json')
    with open(input_json_file_path, 'w') as f:
      json.dump(contents, f)
    try:
      upload_test_results.main([
        '--test-type=foo',
        '--input-json=%s' % input_json_file_path,
        '--results-directory=%s' % result_directory,
        '--test-results-server=foo',
        '--master-name=sauron',
      ])
      files = [
        ('full_results.json',
         os.path.join(result_directory,
                      upload_test_results.FULL_RESULTS_FILENAME)),
        ('times_ms.json',
         os.path.join(result_directory,
                      upload_test_results.TIMES_MS_FILENAME))]
      uploader_mock.assert_called_with(
          'foo',
          [('builder', 'DUMMY_BUILDER_NAME'),
           ('testtype', 'foo'),
           ('master', 'sauron')], files, 120)
    finally:
      shutil.rmtree(result_directory)


if __name__ == '__main__':
  unittest.main()
