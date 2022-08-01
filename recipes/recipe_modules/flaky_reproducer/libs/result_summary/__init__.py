# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .base_result_summary import TestStatus, TestResult, UnexpectedTestResult
from .blink_web_tests_result_summary import BlinkWebTestsResultSummary
from .gtest_result_summary import GTestTestResultSummary


def create_result_summary_from_output_json(json_data):
  """Factory method for TestResultSummary(s) that distinguish and create the
  correct TestResultSummary object."""
  if 'run_histories' in json_data:
    return BlinkWebTestsResultSummary.from_output_json(json_data)
  elif 'per_iteration_data' in json_data:
    return GTestTestResultSummary.from_output_json(json_data)
  raise NotImplementedError('Not Supported output.json format.')
