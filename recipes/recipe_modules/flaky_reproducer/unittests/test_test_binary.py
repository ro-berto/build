# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import io
import json
import unittest
from unittest.mock import patch, mock_open

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
  @patch('logging.info')
  @patch('os.environ', new={'foo': 'bar'})
  def test_run_cmd(self, mock_logging, mock_popen):
    mock_popen.return_value.wait.return_value = 0
    cmd = ['./exec', '--args']
    utils.run_cmd(cmd, env={}, cwd='out\\Release_x64')
    mock_logging.assert_called_once_with('Running %r in %r with %r', cmd,
                                         'out\\Release_x64', {})
    mock_popen.assert_called_once_with(cmd, env={}, cwd='out\\Release_x64')

  @patch('subprocess.Popen')
  @patch('logging.info')
  @patch('os.environ', new={'ISOLATED_OUTDIR': '/isolated_out_dir'})
  def test_run_cmd_with_isolated_outdir(self, mock_logging, mock_popen):
    mock_popen.return_value.wait.return_value = 0
    cmd = ['./exec', '--args', r'--output=${ISOLATED_OUTDIR}']
    utils.run_cmd(cmd, env={}, cwd='out\\Release_x64')
    mock_logging.assert_called_once_with(
        'Running %r in %r with %r',
        ['./exec', '--args', '--output=/isolated_out_dir'], 'out\\Release_x64',
        {})
    mock_popen.assert_called_once_with(
        ['./exec', '--args', '--output=/isolated_out_dir'],
        env={},
        cwd='out\\Release_x64')

  @patch('subprocess.Popen')
  @patch('logging.info')
  @patch('os.environ', new={'foo': 'bar'})
  def test_run_cmd_with_failure(self, mock_logging, mock_popen):
    mock_popen.return_value.wait.return_value = 1
    cmd = ['./exec', '--args']
    ret = utils.run_cmd(cmd, env={}, cwd='out\\Release_x64')
    mock_popen.assert_called_once_with(cmd, env={}, cwd='out\\Release_x64')
    self.assertEqual(ret, 1)


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

  def test_from_jsonish_blink_web_tests(self):
    jsonish = json.loads(get_test_data('blink_web_tests_binary.json'))
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

    # @patch('tempfile.NamedTemporaryFile') for all tests
    tmp_patcher = patch('tempfile.NamedTemporaryFile')
    self.addClassCleanup(tmp_patcher.stop)
    mock_NamedTemporaryFile = tmp_patcher.start()

    def new_NamedTemporaryFile(
        suffix=None,
        prefix=None,
        dir=None,  # pylint: disable=redefined-builtin
        *args,
        **kwargs):
      fp = io.StringIO()
      fp.name = "/{0}/{1}mock-temp-{2}{3}".format(
          dir or 'mock-tmp', prefix or '', mock_NamedTemporaryFile.call_count,
          suffix or '')
      return fp

    mock_NamedTemporaryFile.side_effect = new_NamedTemporaryFile

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

  def test_with_methods(self):
    tests = ['abc.aaa', 'cba.bbb']
    ret = self.test_binary.with_tests(tests)
    self.assertIsNot(ret, self.test_binary)
    self.assertIsNot(ret.tests, tests)
    self.assertEqual(ret.tests, tests)

    ret = self.test_binary.with_repeat(3)
    self.assertIsNot(ret, self.test_binary)
    self.assertEqual(ret.repeat, 3)

  def test_not_implemented(self):
    with self.assertRaisesRegex(NotImplementedError,
                                'Method should be implemented in sub-classes'):
      self.test_binary._get_command()

    with self.assertRaisesRegex(
        NotImplementedError, 'RESULT_SUMMARY_CLS should be set in sub-classes'):
      self.test_binary.run()

  @patch.object(utils, 'run_cmd')
  @patch(
      'builtins.open',
      new=mock_open(read_data=get_test_data('gtest_good_output.json')))
  @patch('os.unlink')
  @patch.object(BaseTestBinary, '_get_command')
  @patch.object(BaseTestBinary, 'RESULT_SUMMARY_CLS')
  def test_run_tests(self, mock_result_cls, mock_get_command, mock_unlink,
                     mock_run_cmd):
    mock_get_command.return_value = ['return', 'command']
    test_binary = self.test_binary.strip_for_bots()
    test_binary.with_tests(['MockUnitTests.CrashTest'] * 2).run()
    mock_result_cls.from_output_json.assert_called()
    mock_get_command.assert_called_once_with(None, '/mock-tmp/mock-temp-1.json')
    mock_run_cmd.assert_called_once_with(['return', 'command'],
                                         cwd=test_binary.cwd)
    mock_unlink.assert_called()

  @patch.object(utils, 'run_cmd')
  @patch(
      'builtins.open',
      new=mock_open(read_data=get_test_data('gtest_good_output.json')))
  @patch('os.unlink')
  @patch.object(BaseTestBinary, '_get_command')
  @patch.object(BaseTestBinary, 'RESULT_SUMMARY_CLS')
  def test_run_tests_with_multiple_tests(self, mock_result_cls,
                                         mock_get_command, mock_unlink,
                                         mock_run_cmd):
    mock_get_command.return_value = ['return', 'command']
    test_binary = self.test_binary.strip_for_bots()
    test_binary.with_tests(['MockUnitTests.CrashTest'] * 20).run()
    mock_result_cls.from_output_json.assert_called()
    mock_get_command.assert_called_once_with('/mock-tmp/mock-temp-1.filter',
                                             '/mock-tmp/mock-temp-2.json')
    mock_run_cmd.assert_called_once_with(['return', 'command'],
                                         cwd=test_binary.cwd)
    mock_unlink.assert_called()

  @patch.object(BaseTestBinary, '_get_command')
  def test_readable_command(self, mock_get_command):
    mock_get_command.return_value = ['return', 'command']
    self.maxDiff = None
    test_binary = self.test_binary.strip_for_bots()
    readable_info = test_binary\
      .with_tests(['MockUnitTests.CrashTest'])\
      .readable_command()
    mock_get_command.assert_called_with(None)
    self.assertEqual(readable_info, 'return command')

    readable_info = test_binary\
      .with_tests(['MockUnitTests.CrashTest']*20)\
      .readable_command()
    mock_get_command.assert_called_with('tests.filter')
    self.assertEqual(readable_info,
                     ('cat <<EOF > tests.filter\n' +
                      ('\n'.join(['MockUnitTests.CrashTest'] * 20)) + '\nEOF\n'
                      'return command'))

  @patch.object(BaseTestBinary, '_get_command')
  def test_as_command(self, mock_get_command):
    mock_get_command.return_value = ['return', 'command']
    self.maxDiff = None
    test_binary = self.test_binary.strip_for_bots()
    command = test_binary\
      .with_tests(['MockUnitTests.CrashTest'])\
      .as_command('${ISOLATED_OUTDIR}/output-$N$.json')
    mock_get_command.assert_called_once_with(
        output_json='${ISOLATED_OUTDIR}/output-$N$.json')
    self.assertEqual(command, ['return', 'command'])

    with self.assertRaisesRegex(
        Exception, 'Too many tests, filter file not supported in as_command'):
      test_binary\
        .with_tests(['MockUnitTests.CrashTest']*20)\
        .as_command()


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

  def test_with_options_from_other(self):

    class NewTestBinary(TestBinaryWithBatchMixin, TestBinaryWithParallelMixin,
                        BaseTestBinary):
      pass

    test_binary = NewTestBinary(['abc'])
    test_binary = (
        test_binary  # go/pyformat-break
        .with_tests(['a', 'b'])  #
        .with_repeat(10)  #
        .with_single_batch()  #
        .with_parallel_jobs(10))
    new_test_binary = NewTestBinary(['abc'])
    new_test_binary = new_test_binary.with_options_from_other(test_binary)
    self.assertDictEqual(test_binary.to_jsonish(), new_test_binary.to_jsonish())
