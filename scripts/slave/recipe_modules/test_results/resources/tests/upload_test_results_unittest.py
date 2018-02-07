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
      os.path.dirname(__file__), '..', '..', '..', '..', '..'))
import common.env
common.env.Install()
import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import upload_test_results


class UploadTestResultsTest(unittest.TestCase):

  def setUp(self):
    pass

  def test_no_test_data(self):
    results = upload_test_results.get_results_map_from({})
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
    results = upload_test_results.get_results_map_from(contents)
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
    results = upload_test_results.get_results_map_from(contents)
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
    results = upload_test_results.get_results_map_from(contents)
    self.assertEquals(results['Disabled.Test'][0].DISABLED,
                      results['Disabled.Test'][0].modifier)
    self.assertEquals(results['Disabled.Test'][0].DISABLED,
                      results['Skipped.Test'][0].modifier)

  @mock.patch('test_results_uploader.upload_test_results')
  def test_main_gtest_json(self, uploader_mock):
    contents = {
        'per_iteration_data': [{
            'Fake.Test': [
                {'status': 'XXX', 'elapsed_time_ms': 1000},
            ],
        }],
    }
    result_directory = tempfile.mkdtemp()
    try:
      input_json_file_path = os.path.join(result_directory, 'results.json')
      with open(input_json_file_path, 'w') as f:
        json.dump(contents, f)
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

  @mock.patch('test_results_uploader.upload_test_results')
  def test_main_full_results_json(self, uploader_mock):
    contents = {
        'tests': {
            'mojom_tests': {
              'parse': {
                'ast_unittest': {
                  'ASTTest': {
                    'testNodeBase': {
                      'expected': 'PASS',
                      'actual': 'PASS'
                    }
                  }
                }
              }
            }
          },
          'interrupted': False,
          'path_delimiter': '.',
          'version': 3,
          'seconds_since_epoch': 1406662283.764424,
          'num_failures_by_type': {
            'FAIL': 0,
            'PASS': 1
          }
    }
    result_directory = tempfile.mkdtemp()
    try:
      input_json_file_path = os.path.join(result_directory, 'results.json')
      with open(input_json_file_path, 'w') as f:
        json.dump(contents, f)
      upload_test_results.main([
        '--test-type=foo',
        '--input-json=%s' % input_json_file_path,
        '--results-directory=%s' % result_directory,
        '--test-results-server=foo',
        '--builder-name=hobbit',
        '--build-number=1234',
        '--build-id=2345',
        '--chrome-revision=99999',
        '--master-name=sauron',
      ])
      uploaded_json_result_path = os.path.join(
          result_directory, upload_test_results.FULL_RESULTS_FILENAME)

      # Assert that metadata are added to the json results before uploading.
      with open(uploaded_json_result_path) as f:
        augmented_json = json.load(f)
      self.assertEquals(augmented_json.get('master_name'), 'sauron')
      self.assertEquals(augmented_json.get('builder_name'), 'hobbit')
      self.assertEquals(augmented_json.get('build_number'), '1234')
      self.assertEquals(augmented_json.get('build_id'), '2345')
      self.assertEquals(augmented_json.get('chromium_revision'), '99999')

      files = [('full_results.json', uploaded_json_result_path)]
      uploader_mock.assert_called_with(
          'foo',
          [('builder', 'hobbit'),
           ('testtype', 'foo'),
           ('master', 'sauron')], files, 120)
    finally:
      shutil.rmtree(result_directory)


if __name__ == '__main__':
  unittest.main()
