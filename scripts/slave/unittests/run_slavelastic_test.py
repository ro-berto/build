#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import os
import socket
import sys
import unittest
import urllib

import test_env  # pylint: disable=W0403,W0611

import slave.run_slavelastic as run_slavelastic

FILE_NAME = "test.results"
TEST_NAME = "unit_tests"

ENV_VARS = {'GTEST_TOTAL_SHARDS': '%(num_instances)s',
            'GTEST_SHARD_INDEX': '%(instance_index)s'}


class Switches(object):
  def __init__(self, working_dir="swarm_tests", min_shards=1, num_shards=1,
               os_image='win32', url='http://localhost:8080'):
    self.working_dir = working_dir
    self.min_shards = min_shards
    self.num_shards = num_shards
    self.os_image = os_image
    self.url = url


class ManifestTest(unittest.TestCase):
  def setUp(self):
    self.hostname = socket.gethostbyname(socket.gethostname()) + ':8080'
    self.filename_url = urllib.pathname2url(
        os.path.relpath(TEST_NAME + '.zip', '../..'))
    self.correct_data = ['http://%s/%s' % (self.hostname, self.filename_url)]


  def GenerateExpectedJSON(self, switches):
    platform_mapping =  {
      'win32': 'Windows',
      'cygwin': 'Windows',
      'linux2': 'Linux',
      'darwin': 'Mac'
      }

    expected = {
      'test_case_name': TEST_NAME,
      'data': self.correct_data,
      'tests' : [
        {
          'action': [
            'python', 'src/tools/isolate/run_test_from_archive.py',
            '-m', FILE_NAME,
            '-r', 'http://' + self.hostname + '/hashtable/'
          ],
          'test_name': 'Run Test'
        }
      ],
      'env_vars': ENV_VARS,
      'configurations': [
        {
          'min_instances': 1,
          'max_instances': 1,
          'config_name': platform_mapping[switches.os_image],
          'dimensions': {
            'os': platform_mapping[switches.os_image],
          },
        },
      ],
      'working_dir': switches.working_dir,
      'cleanup': 'data'
    }

    if switches.os_image == 'win32':
      expected['tests'].append(
          {'action': ['del', 'unit_tests.zip'], 'test_name': 'Clean Up'})
    else:
      expected['tests'].append(
          {'action': ['rm', '-rf', 'unit_tests.zip'], 'test_name': 'Clean Up'})

    if switches.os_image == 'win32':
      expected['tests'].append(
        {
          'action': [
            sys.executable,
            '..\\b\\build\\scripts\\slave\\kill_processes.py'
          ],
          'test_name': 'Kill Processes'
        }
      )

    return expected

  def test_basic_manifest(self):
    switches = Switches()
    manifest = run_slavelastic.Manifest(FILE_NAME, TEST_NAME, switches)

    manifest_json = json.loads(manifest.to_json())

    expected = self.GenerateExpectedJSON(switches)
    self.assertEqual(expected, manifest_json)

  def test_basic_linux(self):
    """A basic linux manifest test to ensure that windows specific values
       aren't used.
    """

    switches = Switches(os_image='linux2')
    manifest = run_slavelastic.Manifest(FILE_NAME, TEST_NAME, switches)

    manifest_json = json.loads(manifest.to_json())

    expected = self.GenerateExpectedJSON(switches)
    self.assertEqual(expected, manifest_json)


if __name__ == '__main__':
  unittest.main()
