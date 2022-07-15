# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import unittest
from unittest.mock import patch, MagicMock

from libs.test_binary import create_test_binary_from_jsonish
from libs.test_binary.gtest_test_binary import GTestTestBinary
from libs.result_summary import (create_result_summary_from_output_json,
                                 TestStatus)
from libs.result_summary.gtest_result_summary import (GTestTestResultSummary,
                                                      GTestTestResult)
from libs.strategies.batch_strategy import BatchStrategy
from testdata import get_test_data


class BatchStrategyTest(unittest.TestCase):

  def setUp(self):
    self.test_binary = create_test_binary_from_jsonish(
        json.loads(get_test_data('gtest_test_binary.json')))
    self.result_summary = create_result_summary_from_output_json(
        json.loads(get_test_data('gtest_good_output.json')))

  def get_strategy(self, test_name):
    return BatchStrategy(self.test_binary, self.result_summary, test_name)

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

  def test_no_batch_id(self):
    strategy = self.get_strategy('MockUnitTests.AnyTest')
    with self.assertRaisesRegex(
        Exception,
        'Batch strategy requires failing sample with not None batch_id.'):
      strategy.run()

  def test_get_batch_tests(self):
    strategy = self.get_strategy('MockUnitTests.FailTest')
    strategy.failing_sample = strategy.result_summary.get_failing_sample(
        strategy.test_name)
    tests = strategy._get_batch_tests()
    self.assertEqual(len(tests), 2)
    self.assertEqual(['MockUnitTests.CrashTest', 'MockUnitTests.PassTest'],
                     [x.test_name for x in tests])

    for t in self.result_summary.get_all('MockUnitTests.CrashTest'):
      t.start_time += 10
    tests = strategy._get_batch_tests()
    self.assertEqual(len(tests), 1)
    self.assertEqual(['MockUnitTests.PassTest'], [x.test_name for x in tests])

  def test_timeout(self):
    strategy = self.get_strategy('MockUnitTests.FailTest')
    reproducing_step = strategy.run(timeout=0)
    self.assertFalse(reproducing_step)

  def test_empty_batch_tests(self):
    failing_sample = self.result_summary.get_failing_sample(
        'MockUnitTests.FailTest')
    failing_sample.batch_id = 654321
    strategy = self.get_strategy('MockUnitTests.FailTest')
    reproducing_step = strategy.run()
    self.assertFalse(reproducing_step)

  @patch.object(GTestTestBinary, 'run', autospec=True)
  def test_find_best_batch_tests(self, mock_test_binary_run):
    # The strategy should verify CrashTest + PassTest with FailTest
    test_self = self

    def mock_test_binary_run_side_effect(self, *args, **kwargs):
      if len(self.tests) == 3:
        return test_self.generate_result_summary(
            'MockUnitTests.FailTest',
            'F',
            primary_error_message=strategy.failing_sample.primary_error_message,
        )
      return test_self.generate_result_summary('MockUnitTests.FailTest', 'P')

    mock_test_binary_run.side_effect = mock_test_binary_run_side_effect

    strategy = self.get_strategy('MockUnitTests.FailTest')
    reproducing_step = strategy.run()
    self.assertEqual(mock_test_binary_run.call_count, 30)
    self.assertEqual(reproducing_step.test_binary.tests, [
        'MockUnitTests.CrashTest', 'MockUnitTests.PassTest',
        'MockUnitTests.FailTest'
    ])

  @patch.object(GTestTestBinary, 'run', autospec=True)
  def test_recursive_find_best_batch_tests(self, mock_test_binary_run):
    # The strategy should verify CrashTest + PassTest with FailTest
    test_self = self

    def mock_test_binary_run_side_effect(self, *args, **kwargs):
      if 'MockUnitTests.CrashTest' in self.tests:
        return test_self.generate_result_summary(
            'MockUnitTests.FailTest',
            'F',
            primary_error_message=strategy.failing_sample.primary_error_message,
        )
      return test_self.generate_result_summary('MockUnitTests.FailTest', 'P')

    mock_test_binary_run.side_effect = mock_test_binary_run_side_effect

    failing_sample = self.result_summary.get_failing_sample(
        'MockUnitTests.FailTest')
    # 1 mins, 1/5 of SINGLE_ROUND_SECONDS
    failing_sample.duration = 60 * 1000

    strategy = self.get_strategy('MockUnitTests.FailTest')
    reproducing_step = strategy.run()
    self.assertEqual(mock_test_binary_run.call_count, 15)
    self.assertEqual(reproducing_step.test_binary.tests,
                     ['MockUnitTests.CrashTest', 'MockUnitTests.FailTest'])

  @patch.object(GTestTestBinary, 'run')
  def test_not_executed_error(self, mock_test_binary_run):
    mock_test_binary_run.return_value = self.generate_result_summary(None, '')
    strategy = self.get_strategy('MockUnitTests.FailTest')
    with self.assertRaisesRegex(
        KeyError, "Target test wasn't executed during reproducing"):
      strategy.run()
