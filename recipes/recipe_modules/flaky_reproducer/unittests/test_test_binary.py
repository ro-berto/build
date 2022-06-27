# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import io
import json
import unittest
from unittest.mock import patch

from libs.test_binary.base_test_binary import (BaseTestBinary,
                                               strip_command_switches)
from testdata import get_test_data


class BaseTestBinaryTest(unittest.TestCase):

  def setUp(self):
    jsonish = json.loads(get_test_data('gtest_test_binary.json'))
    self.test_binary = BaseTestBinary.from_jsonish(jsonish)

  def test_from_to_jsonish(self):
    self.maxDiff = None
    jsonish = json.loads(get_test_data('gtest_test_binary.json'))
    test_binary = BaseTestBinary.from_jsonish(jsonish)
    to_jsonish = test_binary.to_jsonish()
    self.assertEqual(to_jsonish, jsonish)

  def test_strip_command_switches(self):
    self.assertEqual(
        strip_command_switches(['--foo', '1', '2', '3', '4'], {'foo': 0}),
        ['1', '2', '3', '4'])
    self.assertEqual(
        strip_command_switches(['--foo', '1', '2', '3', '4'], {'foo': 2}),
        ['3', '4'])
    self.assertEqual(
        strip_command_switches(['--foo', '1', '--bar', '3', '4'], {'foo': 2}),
        ['--bar', '3', '4'])
    self.assertEqual(
        strip_command_switches(['--foo', '1', '--bar', '3', '4'], {
            'foo': 2,
            'bar': 1
        }), ['4'])
    # --switch=value shouldn't take multiple values.
    self.assertEqual(
        strip_command_switches(['--foo=1', '--foo=2', '1', '2', '3', '4'],
                               {'foo': 2}), ['1', '2', '3', '4'])
    # I don't know if -foo= 1 2 is valid, but I would expect following behavior.
    self.assertEqual(
        strip_command_switches(['--foo=', '1', '2', '3', '4'], {'foo': 2}),
        ['3', '4'])

  def test_strip_for_bots(self):
    test_binary = self.test_binary.strip_for_bots()
    self.assertEqual(test_binary.command, [
        "vpython3",
        "../../testing/test_env.py",
        "./base_unittests.exe",
        "--test-launcher-bot-mode",
        "--asan=0",
        "--lsan=0",
        "--msan=0",
        "--tsan=0",
        "--cfi-diag=0",
        "--test-launcher-summary-output=${ISOLATED_OUTDIR}/output.json",
    ])
    self.assertNotIn('LLVM_PROFILE_FILE', test_binary.env_vars)

  def test_strip_for_bots_should_return_a_copy(self):
    new_test_binary = self.test_binary.strip_for_bots()
    self.assertNotIn('a', new_test_binary.env_vars)
    new_test_binary.env_vars['a'] = 'b'
    self.assertIn('a', new_test_binary.env_vars)
    self.assertNotIn('a', self.test_binary.env_vars)
    self.assertIsNot(new_test_binary.command, self.test_binary.command)
    self.assertIsNot(new_test_binary.env_vars, self.test_binary.env_vars)
    self.assertIsNot(new_test_binary.dimensions, self.test_binary.dimensions)

  def test_strip_for_bots_should_raise_exceptions(self):
    test_binary = BaseTestBinary(['rdb', '--abc', './test'])
    with self.assertRaisesRegex(ValueError, 'Unsupported command wrapper:'):
      test_binary.strip_for_bots()

    test_binary = BaseTestBinary(['rdb', '--'])
    with self.assertRaisesRegex(ValueError, 'Empty command after strip:'):
      test_binary.strip_for_bots()

    test_binary = BaseTestBinary(['rdb', '--', 'echo', '123'])
    with self.assertRaisesRegex(ValueError,
                                'Command line contains unknown wrapper:'):
      test_binary.strip_for_bots()

  @patch('subprocess.Popen')
  @patch('sys.stderr', new_callable=io.StringIO)
  @patch('os.environ', new={'foo': 'bar'})
  def test_run_cmd(self, mock_stdout, mock_popen):
    cmd = ['./exec', '--args']
    self.test_binary.run_cmd(cmd)
    self.assertEqual(mock_stdout.getvalue(),
                     "Running ['./exec', '--args'] in 'out\\\\Release_x64'\n")
    mock_popen.assert_called_once_with(cmd, cwd='out\\Release_x64')

  @patch('subprocess.Popen')
  @patch('sys.stderr', new_callable=io.StringIO)
  def test_run_cmd_should_override_cwd(self, mock_stdout, mock_popen):
    cmd = ['./exec', '--args']
    self.test_binary.run_cmd(cmd, cwd='somewhere')
    self.assertEqual(mock_stdout.getvalue(),
                     "Running ['./exec', '--args'] in 'somewhere'\n")
    mock_popen.assert_called_once_with(cmd, cwd='somewhere')

  def test_should_not_implement_in_base_class(self):
    with self.assertRaises(NotImplementedError):
      self.test_binary.run_tests([], 1)
