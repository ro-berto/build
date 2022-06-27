# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import io
import json
import unittest
from unittest.mock import patch

from libs.test_binary import utils, create_test_binary_from_jsonish
from libs.test_binary.base_test_binary import (BaseTestBinary,
                                               TestBinaryWithBatchMixin,
                                               TestBinaryWithParallelMixin)
from testdata import get_test_data


class TestBinaryUtilsTest(unittest.TestCase):

  def test_strip_command_switches(self):
    self.assertEqual(
        utils.strip_command_switches(['--foo', '1', '2', '3', '4'], {'foo': 0}),
        ['1', '2', '3', '4'])
    self.assertEqual(
        utils.strip_command_switches(['--foo', '1', '2', '3', '4'], {'foo': 2}),
        ['3', '4'])
    self.assertEqual(
        utils.strip_command_switches(['--foo', '1', '--bar', '3', '4'],
                                     {'foo': 2}), ['--bar', '3', '4'])
    self.assertEqual(
        utils.strip_command_switches(['--foo', '1', '--bar', '3', '4'], {
            'foo': 2,
            'bar': 1
        }), ['4'])
    # --switch=value shouldn't take multiple values.
    self.assertEqual(
        utils.strip_command_switches(['--foo=1', '--foo=2', '1', '2', '3', '4'],
                                     {'foo': 2}), ['1', '2', '3', '4'])
    # I don't know if -foo= 1 2 is valid, but I would expect following behavior.
    self.assertEqual(
        utils.strip_command_switches(['--foo=', '1', '2', '3', '4'],
                                     {'foo': 2}), ['3', '4'])

  @patch('subprocess.Popen')
  @patch('sys.stderr', new_callable=io.StringIO)
  @patch('os.environ', new={'foo': 'bar'})
  def test_run_cmd(self, mock_stdout, mock_popen):
    mock_popen.return_value.wait.return_value = 0
    cmd = ['./exec', '--args']
    utils.run_cmd(cmd, env={}, cwd='out\\Release_x64')
    self.assertEqual(
        mock_stdout.getvalue(),
        "Running ['./exec', '--args'] in 'out\\\\Release_x64' with {}\n")
    mock_popen.assert_called_once_with(cmd, env={}, cwd='out\\Release_x64')

  @patch('subprocess.Popen')
  @patch('sys.stderr', new_callable=io.StringIO)
  @patch('os.environ', new={'foo': 'bar'})
  def test_run_cmd_with_failure(self, mock_stdout, mock_popen):
    mock_popen.return_value.wait.return_value = 1
    cmd = ['./exec', '--args']
    with self.assertRaises(ChildProcessError):
      utils.run_cmd(cmd, env={}, cwd='out\\Release_x64')
    mock_popen.assert_called_once_with(cmd, env={}, cwd='out\\Release_x64')


class TestBinaryFactoryTest(unittest.TestCase):

  def setUp(self):
    self.maxDiff = None

  def test_from_jsonish_no_class_name(self):
    jsonish = json.loads(get_test_data('gtest_test_binary.json'))
    jsonish.pop('class_name')
    with self.assertRaises(ValueError):
      create_test_binary_from_jsonish(jsonish)

  def test_from_jsonish_unknown_class_name(self):
    jsonish = json.loads(get_test_data('gtest_test_binary.json'))
    jsonish['class_name'] = 'UnknownTestBinary'
    with self.assertRaises(ValueError):
      create_test_binary_from_jsonish(jsonish)

  def test_to_jsonish_should_support_with_methods(self):
    jsonish = json.loads(get_test_data('gtest_test_binary_with_overrides.json'))
    test_binary = create_test_binary_from_jsonish(jsonish)
    test_binary = test_binary.with_tests([
        "MockUnitTests.CrashTest", "MockUnitTests.PassTest"
    ]).with_repeat(3).with_single_batch().with_parallel_jobs(5)
    to_jsonish = test_binary.to_jsonish()
    test_binary_from_jsonish = create_test_binary_from_jsonish(to_jsonish)
    self.assertEqual(test_binary_from_jsonish.tests, test_binary.tests)
    self.assertEqual(test_binary_from_jsonish.repeat, test_binary.repeat)
    self.assertEqual(test_binary_from_jsonish.single_batch,
                     test_binary.single_batch)
    self.assertEqual(test_binary_from_jsonish.parallel_jobs,
                     test_binary.parallel_jobs)

  def test_from_jsonish(self):
    jsonish = json.loads(get_test_data('gtest_test_binary.json'))
    test_binary = create_test_binary_from_jsonish(jsonish)
    to_jsonish = test_binary.to_jsonish()
    self.assertEqual(to_jsonish, jsonish)

  def test_from_jsonish_with_overrides(self):
    jsonish = json.loads(get_test_data('gtest_test_binary_with_overrides.json'))
    test_binary = create_test_binary_from_jsonish(jsonish)
    to_jsonish = test_binary.to_jsonish()
    self.assertEqual(to_jsonish, jsonish)


class BaseTestBinaryTest(unittest.TestCase):

  def setUp(self):
    # Note: BaseTestBinary can not created via create_test_binary_from_jsonish
    jsonish = json.loads(get_test_data('gtest_test_binary.json'))
    self.test_binary = BaseTestBinary.from_jsonish(jsonish)

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

  def test_with_methods(self):
    tests = ['abc.aaa', 'cba.bbb']
    ret = self.test_binary.with_tests(tests)
    self.assertIsNot(ret, self.test_binary)
    self.assertIsNot(ret.tests, tests)
    self.assertEqual(ret.tests, tests)

    ret = self.test_binary.with_repeat(3)
    self.assertIsNot(ret, self.test_binary)
    self.assertEqual(ret.repeat, 3)

  def test_should_not_implement_in_base_class(self):
    with self.assertRaises(NotImplementedError):
      self.test_binary.run()
    with self.assertRaises(NotImplementedError):
      self.test_binary.readable_command()


class TestBinaryMixinTest(unittest.TestCase):

  def test_TestBinaryWithBatchMixin(self):

    class NewTestBinary(TestBinaryWithBatchMixin, BaseTestBinary):
      pass

    test_binary = NewTestBinary(['abc'])
    self.assertEqual(test_binary.command, ['abc'])
    self.assertTrue(hasattr(test_binary, 'with_single_batch'))
    ret = test_binary.with_single_batch()
    self.assertTrue(ret.single_batch)

  def test_TestBinaryWithParallelMixin(self):

    class NewTestBinary(TestBinaryWithParallelMixin, BaseTestBinary):
      pass

    test_binary = NewTestBinary(['abc'])
    self.assertEqual(test_binary.command, ['abc'])
    self.assertTrue(hasattr(test_binary, 'with_parallel_jobs'))
    ret = test_binary.with_parallel_jobs(3)
    self.assertEqual(ret.parallel_jobs, 3)
