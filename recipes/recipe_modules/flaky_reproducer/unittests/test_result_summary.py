# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import unittest
from unittest.mock import patch

from libs.result_summary import (create_result_summary_from_output_json,
                                 TestResult, TestStatus)
from libs.result_summary.base_result_summary import BaseResultSummary
from libs.result_summary.gtest_result_summary import GTestTestResultSummary
from testdata import get_test_data


class ResultSummaryFactoryTest(unittest.TestCase):

  @patch.object(GTestTestResultSummary, 'from_output_json')
  def test_gtest(self, mock_from_output_json):
    json_data = json.loads(get_test_data('gtest_good_output.json'))
    create_result_summary_from_output_json(json_data)
    mock_from_output_json.assert_called_with(json_data)

  def test_test_result(self):
    pass_result = TestResult('test.foo.bar.pass', True, TestStatus.PASS)
    self.assertTrue(pass_result.is_valid())
    self.assertEqual(repr(pass_result), 'PASS(expected) - test.foo.bar.pass')

    fail_result = TestResult('test.foo.bar.fail', False, TestStatus.FAIL)
    self.assertTrue(fail_result.is_valid())
    self.assertEqual(repr(fail_result), 'FAIL(unexpected) - test.foo.bar.fail')

    skip_result = TestResult('test.foo.bar.skip', True, TestStatus.SKIP)
    self.assertTrue(skip_result.is_valid())
    self.assertEqual(repr(skip_result), 'SKIP(expected) - test.foo.bar.skip')

    invalid_result = TestResult(
        'test.foo.bar.invalid', status=TestStatus.STATUS_UNSPECIFIED)
    self.assertFalse(invalid_result.is_valid())
    self.assertEqual(
        repr(invalid_result),
        'STATUS_UNSPECIFIED(unexpected) - test.foo.bar.invalid')

  def test_should_not_implement_in_base(self):
    result_summary = BaseResultSummary()
    with self.assertRaises(NotImplementedError):
      result_summary.dump_raw_data()
