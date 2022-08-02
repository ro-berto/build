# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import logging

from .base_result_summary import (BaseResultSummary, TestStatus, TestResult,
                                  TestResultErrorMessageRegexSimilarityMixin)


class BlinkWebTestsResult(TestResultErrorMessageRegexSimilarityMixin,
                          TestResult):
  pass


# https://source.chromium.org/chromium/chromium/src/+/main:third_party/blink/tools/blinkpy/web_tests/controllers/test_result_sink.py;l=30;drc=989707b1b913a79ff90257727e0464782e1e4fa1
BLINK_WEB_TESTS_STATUS_MAP = {
    'PASS': TestStatus.PASS,
    'FAIL': TestStatus.FAIL,
    'TIMEOUT': TestStatus.ABORT,
    'Aborted': TestStatus.ABORT,
    'CRASH': TestStatus.CRASH,
    'SKIP': TestStatus.SKIP,
}


class BlinkWebTestsResultSummary(BaseResultSummary):
  FORMAT_ERROR = ValueError(
      'Not supported Blink Web Tests output format. ',
      'Please make sure the output.json is generated by '
      '--write-run-histories-to')

  def __init__(self):
    super().__init__()
    self._raw_data = None

  @classmethod
  def from_output_json(cls, json_data):
    if (not isinstance(json_data, dict) or 'run_histories' not in json_data or
        not isinstance(json_data['run_histories'], list)):
      raise cls.FORMAT_ERROR

    result = cls()
    result._raw_data = json_data
    # third_party/blink/tools/blinkpy/web_tests/models/test_run_results.py
    for test_result in json_data['run_histories']:
      try:
        primary_error_message = test_result.get('failure_reason',
                                                {}).get('primary_error_message')
        if not primary_error_message and test_result.get('failures'):
          primary_error_message = test_result['failures'][0]['message']
        result.add(
            BlinkWebTestsResult(
                test_result['test_name'],
                expected=(
                    test_result['type'] in test_result['expected_results']),
                status=BLINK_WEB_TESTS_STATUS_MAP.get(
                    test_result['type'], TestStatus.STATUS_UNSPECIFIED),
                primary_error_message=primary_error_message,
                start_time=test_result.get('start_time'),
                duration=test_result.get('total_run_time') * 1000,
                batch_id=test_result.get('pid'),
                thread_id=test_result.get('worker_number'),
            ))
      except KeyError as err:
        logging.error('Unexpected BlinkWebTests result format: %s', err)
        raise cls.FORMAT_ERROR
    return result

  def dump_raw_data(self):
    return json.dumps(self._raw_data)