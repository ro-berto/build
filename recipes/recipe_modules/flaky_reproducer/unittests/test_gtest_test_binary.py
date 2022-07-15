# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import io
import json
import unittest
from unittest.mock import patch, mock_open

from libs.test_binary import utils
from libs.test_binary.gtest_test_binary import GTestTestBinary
from testdata import get_test_data


class GTestTestBinaryTest(unittest.TestCase):

  def setUp(self):
    jsonish = json.loads(get_test_data('gtest_test_binary.json'))
    self.test_binary = GTestTestBinary.from_jsonish(jsonish)

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
    ])
    self.assertNotIn('LLVM_PROFILE_FILE', test_binary.env_vars)

    # should strip GTEST_STRIP_SWITCHES with it's value
    test_binary = GTestTestBinary([
        "./unittests",
        "--gtest_filter=AAA.bbb",
        # should be kept as it's a switch named "gtest_filte AAA.bbb"
        "--gtest_filte AAA.bbb",
        "--isolated-script-test-filter",
        "AAA.bbb",
        "--isolated-script-test-repeat",
        # should be kept as it's not an value of switch
        "--gtest_also_run_disabled_tests",
        "--test-launcher-filter-file",
    ])
    self.assertEqual(test_binary.strip_for_bots().command, [
        "./unittests",
        "--gtest_filte AAA.bbb",
        "--gtest_also_run_disabled_tests",
    ])

    test_binary = GTestTestBinary(['rdb', '--', 'echo', '123'])
    with self.assertRaisesRegex(ValueError,
                                'Command line contains unknown wrapper:'):
      test_binary.strip_for_bots()

  @patch.object(utils, 'run_cmd')
  @patch(
      'builtins.open',
      new=mock_open(read_data=get_test_data('gtest_good_output.json')))
  @patch('os.unlink')
  def test_run_tests(self, mock_unlink, mock_run_cmd):
    test_binary = self.test_binary.strip_for_bots()
    test_binary.with_tests(
        ['MockUnitTests.CrashTest'] *
        2).with_repeat(1).with_single_batch().with_parallel_jobs(1).run()
    mock_run_cmd.assert_called_once_with([
        'vpython3', '../../testing/test_env.py', './base_unittests.exe',
        '--test-launcher-bot-mode', '--asan=0', '--lsan=0', '--msan=0',
        '--tsan=0', '--cfi-diag=0', '--test-launcher-retry-limit=0',
        ('--isolated-script-test-filter='
         'MockUnitTests.CrashTest:MockUnitTests.CrashTest'),
        '--isolated-script-test-repeat=1', '--test-launcher-batch-limit=0',
        '--test-launcher-jobs=1',
        '--test-launcher-summary-output=/mock-tmp/mock-temp-1.json'
    ],
                                         cwd=test_binary.cwd)
    mock_unlink.assert_called()

  @patch.object(utils, 'run_cmd')
  @patch(
      'builtins.open',
      new=mock_open(read_data=get_test_data('gtest_good_output.json')))
  @patch('os.unlink')
  def test_run_tests_with_multiple_tests(self, mock_unlink, mock_run_cmd):
    test_binary = self.test_binary.strip_for_bots()
    test_binary.with_tests(['MockUnitTests.CrashTest'] * 10).run()
    mock_run_cmd.assert_called_once_with(
        [
            'vpython3', '../../testing/test_env.py', './base_unittests.exe',
            '--test-launcher-bot-mode', '--asan=0', '--lsan=0', '--msan=0',
            '--tsan=0', '--cfi-diag=0', '--test-launcher-retry-limit=0',
            '--test-launcher-filter-file=/mock-tmp/mock-temp-1.filter',
            '--test-launcher-summary-output=/mock-tmp/mock-temp-2.json'
        ],  #
        cwd=test_binary.cwd)
    mock_unlink.assert_called()

  def test_readable_command(self):
    self.maxDiff = None
    test_binary = self.test_binary.strip_for_bots()
    readable_info = test_binary\
      .with_tests(['MockUnitTests.CrashTest'])\
      .readable_command()
    self.assertEqual(
        readable_info,
        ('vpython3 ../../testing/test_env.py ./base_unittests.exe'
         ' --test-launcher-bot-mode --asan=0 --lsan=0 --msan=0 --tsan=0'
         ' --cfi-diag=0 --test-launcher-retry-limit=0'
         ' --isolated-script-test-filter=MockUnitTests.CrashTest'))

    readable_info = test_binary\
      .with_tests(['MockUnitTests.CrashTest']*10)\
      .readable_command()
    self.assertEqual(
        readable_info,
        ('''cat <<EOF > tests.filter
MockUnitTests.CrashTest
MockUnitTests.CrashTest
MockUnitTests.CrashTest
MockUnitTests.CrashTest
MockUnitTests.CrashTest
MockUnitTests.CrashTest
MockUnitTests.CrashTest
MockUnitTests.CrashTest
MockUnitTests.CrashTest
MockUnitTests.CrashTest
EOF
'''
         'vpython3 ../../testing/test_env.py ./base_unittests.exe'
         ' --test-launcher-bot-mode --asan=0 --lsan=0 --msan=0 --tsan=0'
         ' --cfi-diag=0 --test-launcher-retry-limit=0'
         ' --test-launcher-filter-file=tests.filter'))

  def test_as_command(self):
    self.maxDiff = None
    test_binary = self.test_binary.strip_for_bots()
    command = test_binary\
      .with_tests(['MockUnitTests.CrashTest'])\
      .as_command('${ISOLATED_OUTDIR}/output-$N$.json')
    self.assertEqual(command, [
        'vpython3', '../../testing/test_env.py', './base_unittests.exe',
        '--test-launcher-bot-mode', '--asan=0', '--lsan=0', '--msan=0',
        '--tsan=0', '--cfi-diag=0', '--test-launcher-retry-limit=0',
        '--isolated-script-test-filter=MockUnitTests.CrashTest',
        '--test-launcher-summary-output=${ISOLATED_OUTDIR}/output-$N$.json'
    ])

    with self.assertRaisesRegex(
        Exception, 'Too many tests, filter file not supported in as_command'):
      test_binary\
        .with_tests(['MockUnitTests.CrashTest']*10)\
        .as_command()

  @patch('os.unlink')
  def test_with_single_batch_with_repeat_raise_error(self, mock_unlink):
    self.test_binary.with_single_batch().as_command()
    with self.assertRaisesRegex(
        Exception, "Can't repeat the tests with single batch in GTest."):
      self.test_binary.with_single_batch().with_repeat(2).as_command()
    with self.assertRaisesRegex(
        Exception, "Can't repeat the tests with single batch in GTest."):
      self.test_binary.with_single_batch().with_repeat(2).run()
    with self.assertRaisesRegex(
        Exception, "Can't repeat the tests with single batch in GTest."):
      self.test_binary.with_single_batch().with_repeat(2).readable_command()
