#!/usr/bin/env vpython
# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import os
import subprocess
import sys
import unittest

import mock

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,
                os.path.abspath(os.path.join(THIS_DIR, os.pardir, 'resources')))

import merge_profiles
import merge_steps
import merger


class MergeProfilesTest(unittest.TestCase):

  def test_merge_script_api_parameters(self):
    """Test the step-level merge front-end."""
    build_properties = json.dumps({
        'some': {
            'complicated': ['nested', {
                'json': None,
                'object': 'thing',
            }]
        }
    })
    task_output_dir = 'some/task/output/dir'
    profdata_dir = '/some/different/path/to/profdata/default.profdata'
    profdata_file = os.path.join(profdata_dir, 'default.profdata')
    args = [
        'script_name', '--output-json', 'output.json', '--build-properties',
        build_properties, '--summary-json', 'summary.json', '--task-output-dir',
        task_output_dir, '--profdata-dir', profdata_dir, '--llvm-profdata',
        'llvm-profdata', 'a.json', 'b.json', 'c.json'
    ]
    with mock.patch.object(merger, 'merge_profiles') as mock_merge:
      with mock.patch.object(sys, 'argv', args):
        merge_profiles.main()
        self.assertEqual(
            mock_merge.call_args,
            mock.call(task_output_dir, profdata_file, '.profraw',
                      'llvm-profdata'))

  def test_merge_steps_parameters(self):
    """Test the build-level merge front-end."""
    input_dir = 'some/task/output/dir'
    output_file = '/some/different/path/to/profdata/merged.profdata'
    args = [
        'script_name',
        '--input-dir',
        input_dir,
        '--output-file',
        output_file,
        '--llvm-profdata',
        'llvm-profdata',
    ]
    with mock.patch.object(merger, 'merge_profiles') as mock_merge:
      with mock.patch.object(sys, 'argv', args):
        merge_steps.main()
        self.assertEqual(
            mock_merge.call_args,
            mock.call(input_dir, output_file, '.profdata', 'llvm-profdata'))

  def test_merge_profraw(self):
    mock_input_dir_walk = [
        ('/b/some/path', ['0', '1', '2', '3'], ['summary.json']),
        ('/b/some/path/0', [],
         ['output.json', 'default-1.profraw', 'default-2.profraw']),
        ('/b/some/path/1', [],
         ['output.json', 'default-1.profraw', 'default-2.profraw']),
        ('/b/some/path/2', [],
         ['output.json', 'default-1.profraw', 'default-2.profraw']),
        ('/b/some/path/3', [],
         ['output.json', 'default-1.profraw', 'default-2.profraw']),
    ]
    with mock.patch.object(os, 'walk') as mock_walk:
      with mock.patch.object(os, 'remove'):
        mock_walk.return_value = mock_input_dir_walk
        with mock.patch.object(subprocess, 'check_output') as mock_exec_cmd:
          merger.merge_profiles('/b/some/path', 'output/dir/default.profdata',
                                '.profraw', 'llvm-profdata')
          self.assertEqual(
              mock.call([
                  'llvm-profdata', 'merge', '-o', 'output/dir/default.profdata',
                  '-sparse=true', '/b/some/path/0/default-1.profraw',
                  '/b/some/path/0/default-2.profraw',
                  '/b/some/path/1/default-1.profraw',
                  '/b/some/path/1/default-2.profraw',
                  '/b/some/path/2/default-1.profraw',
                  '/b/some/path/2/default-2.profraw',
                  '/b/some/path/3/default-1.profraw',
                  '/b/some/path/3/default-2.profraw'
              ]), mock_exec_cmd.call_args)

  def test_merge_profdata(self):
    mock_input_dir_walk = [
        ('/b/some/path', ['base_unittests', 'url_unittests'], ['summary.json']),
        ('/b/some/path/base_unittests', [], ['output.json',
                                             'default.profdata']),
        ('/b/some/path/url_unittests', [], ['output.json', 'default.profdata']),
    ]
    with mock.patch.object(os, 'walk') as mock_walk:
      with mock.patch.object(os, 'remove'):
        mock_walk.return_value = mock_input_dir_walk
        with mock.patch.object(subprocess, 'check_output') as mock_exec_cmd:
          merger.merge_profiles('/b/some/path', 'output/dir/default.profdata',
                                '.profdata', 'llvm-profdata')
          self.assertEqual(
              mock.call([
                  'llvm-profdata',
                  'merge',
                  '-o',
                  'output/dir/default.profdata',
                  '-sparse=true',
                  '/b/some/path/base_unittests/default.profdata',
                  '/b/some/path/url_unittests/default.profdata',
              ]), mock_exec_cmd.call_args)


if __name__ == '__main__':
  unittest.main()
