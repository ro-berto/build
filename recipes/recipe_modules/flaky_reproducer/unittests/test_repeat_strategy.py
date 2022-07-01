# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import unittest
from unittest.mock import patch

from libs.test_binary import create_test_binary_from_jsonish
from libs.test_binary.gtest_test_binary import GTestTestBinary
from libs.result_summary import (create_result_summary_from_output_json,
                                 TestStatus)
from libs.result_summary.gtest_result_summary import (GTestTestResultSummary,
                                                      GTestTestResult)
from libs.strategies.repeat_strategy import RepeatStrategy
from testdata import get_test_data


class BaseStrategyTest(unittest.TestCase):

  def setUp(self):
    self.test_binary = create_test_binary_from_jsonish(
        json.loads(get_test_data('gtest_test_binary.json')))
    self.result_summary = create_result_summary_from_output_json(
        json.loads(get_test_data('gtest_good_output.json')))

  def generate_result_summary(self, test_name, seq, **kwargs):
    result_summary = GTestTestResultSummary()
    for s in seq:
      result_summary.add(
          GTestTestResult(
              test_name,
              expected=(s == 'P'),
              status=(TestStatus.PASS if s == 'P' else TestStatus.FAIL),
              **kwargs))
    return result_summary

  @patch.object(GTestTestBinary, 'run')
  def test_run_reproduced(self, mock_test_binary_run):
    strategy = RepeatStrategy(self.test_binary, self.result_summary,
                              'MockUnitTests.AnyTest')
    mock_test_binary_run.return_value = self.generate_result_summary(
        'MockUnitTests.AnyTest', 'PPPFP', duration=2)
    reproducing_step = strategy.run()
    self.assertEqual(mock_test_binary_run.call_count, 3)
    self.assertEqual(reproducing_step.debug_info['reproduced_cnt'], 3)
    self.assertEqual(reproducing_step.debug_info['total_retries'], 15)

  @patch.object(GTestTestBinary, 'run')
  def test_run_raise_error_if_no_test_executed(self, mock_test_binary_run):
    strategy = RepeatStrategy(self.test_binary, self.result_summary,
                              'MockUnitTests.FailTest')
    mock_test_binary_run.return_value = self.generate_result_summary(
        'MockUnitTests.FailTest', '')
    with self.assertRaisesRegex(
        KeyError, r"Target test wasn't executed during reproducing: .*"):
      strategy.run()

  @patch.object(GTestTestBinary, 'run')
  def test_run_not_reproduced_message_not_match(self, mock_test_binary_run):
    strategy = RepeatStrategy(self.test_binary, self.result_summary,
                              'MockUnitTests.FailTest')
    mock_test_binary_run.return_value = self.generate_result_summary(
        'MockUnitTests.FailTest', 'PPPFP')
    reproducing_step = strategy.run()
    self.assertEqual(mock_test_binary_run.call_count, 200)
    self.assertEqual(reproducing_step.debug_info['reproduced_cnt'], 0)
    self.assertEqual(reproducing_step.debug_info['total_retries'], 1000)

  @patch.object(GTestTestBinary, 'run')
  def test_run_reproduced_message_match(self, mock_test_binary_run):
    strategy = RepeatStrategy(self.test_binary, self.result_summary,
                              'MockUnitTests.FailTest')
    mock_test_binary_run.return_value = self.generate_result_summary(
        'MockUnitTests.FailTest',
        'PPPFP',
        primary_error_message="Value of: false\n  Actual: false\nExpected: true"
    )
    reproducing_step = strategy.run()
    self.assertEqual(mock_test_binary_run.call_count, 3)
    self.assertEqual(reproducing_step.debug_info['reproduced_cnt'], 3)
    self.assertEqual(reproducing_step.debug_info['total_retries'], 15)

  @patch('time.time')
  @patch.object(GTestTestBinary, 'run')
  def test_run_timeout(self, mock_test_binary_run, mock_time):
    strategy = RepeatStrategy(self.test_binary, self.result_summary,
                              'MockUnitTests.AnyTest')
    mock_time.return_value = 0

    def mocked_test_binary_run(*_, **__):
      mock_time.return_value += 60
      return self.generate_result_summary(
          'MockUnitTests.AnyTest', 'PPPPP', duration=2)

    mock_test_binary_run.side_effect = mocked_test_binary_run
    strategy.run(timeout=50 * 60)
    self.assertEqual(mock_test_binary_run.call_count, 45)

  def test_generate_reproducing_step(self):
    strategy = RepeatStrategy(self.test_binary, self.result_summary,
                              'MockUnitTests.AnyTest')
    with self.assertRaisesRegex(
        Exception, 'Cannot generate reproducing step without running history.'):
      strategy._generate_reproducing_step(0, [])
