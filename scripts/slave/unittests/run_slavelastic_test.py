#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import unittest

import test_env  # pylint: disable=W0403,W0611

import slave.run_slavelastic as run_slavelastic

FILE_NAME = "test.results"
TEST_NAME = "unit_tests"
CLEANUP_SCRIPT_NAME = 'swarm_cleanup.py'

ENV_VARS = {'GTEST_TOTAL_SHARDS': '%(num_instances)s',
            'GTEST_SHARD_INDEX': '%(instance_index)s'}


class Options(object):
  def __init__(self, working_dir="swarm_tests", min_shards=1, num_shards=1,
               os_image='win32', url='http://localhost:8080',
               data_url='http://www.google.com/data',
               data_dest_dir='temp_data'):
    self.working_dir = working_dir
    self.min_shards = min_shards
    self.num_shards = num_shards
    self.os_image = os_image
    self.url = url
    self.data_url = data_url
    self.data_dest_dir = data_dest_dir


def GenerateExpectedJSON(options):
  platform_mapping =  {
    'cygwin': 'Windows',
    'darwin': 'Mac',
    'linux2': 'Linux',
    'win32': 'Windows'
  }

  expected = {
    'test_case_name': TEST_NAME,
    'data': [options.data_url + '/' + TEST_NAME + '.zip'],
    'tests' : [
      {
        'action': [
          'python', 'src/tools/isolate/run_test_from_archive.py',
          '-m', FILE_NAME,
          '-r', options.data_url
        ],
        'test_name': 'Run Test',
        'time_out': 600
      },
      {
        'action' : [
            'python', CLEANUP_SCRIPT_NAME
        ],
        'test_name': 'Clean Up',
        'time_out': 600
      }
    ],
    'env_vars': ENV_VARS,
    'configurations': [
      {
        'min_instances': 1,
        'max_instances': 1,
        'config_name': platform_mapping[options.os_image],
        'dimensions': {
          'os': platform_mapping[options.os_image],
        },
      },
    ],
    'working_dir': options.working_dir,
    'cleanup': 'data'
  }

  if options.os_image == 'win32':
    expected['tests'].append(
      {
        'action': [
          'python',
          'kill_processes.py',
          '--handle_exe',
          'handle.exe'
        ],
        'test_name': 'Kill Processes',
        'time_out': 600
      }
    )

  return expected


class ManifestTest(unittest.TestCase):
  def test_basic_manifest(self):
    options = Options()
    manifest = run_slavelastic.Manifest(FILE_NAME, TEST_NAME, options)

    manifest_json = json.loads(manifest.to_json())

    expected = GenerateExpectedJSON(options)
    self.assertEqual(expected, manifest_json)

  def test_basic_linux(self):
    """A basic linux manifest test to ensure that windows specific values
       aren't used.
    """

    options = Options(os_image='linux2')
    manifest = run_slavelastic.Manifest(FILE_NAME, TEST_NAME, options)

    manifest_json = json.loads(manifest.to_json())

    expected = GenerateExpectedJSON(options)
    self.assertEqual(expected, manifest_json)


if __name__ == '__main__':
  unittest.main()
