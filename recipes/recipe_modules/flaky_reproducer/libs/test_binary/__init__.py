# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from .base_test_binary import (BaseTestBinary, TestBinaryWithBatchMixin,
                               TestBinaryWithParallelMixin)
from .gtest_test_binary import GTestTestBinary
from .blink_web_tests_binary import BlinkWebTestsBinary

TEST_BINARIES = {
    GTestTestBinary.__name__: GTestTestBinary,
    BlinkWebTestsBinary.__name__: BlinkWebTestsBinary,
}


def create_test_binary_from_task_request(task_request):
  """Factory method for TestBinary(s) that distinguish and create the correct
  TestBinary object."""
  if len(task_request) < 1:
    raise ValueError("No TaskSlice found in the TaskRequest.")
  request_slice = task_request[-1]
  command = ' '.join(request_slice.command)
  if re.search('result_adapter(.exe)? gtest', command):
    return GTestTestBinary.from_task_request(task_request)
  # android device tests (e.g. android-12-x64-rel) are not using
  # result_adapter, detecting --test-launcher-summary-output as a workaround
  # as it doesn't exists in blink_web_tests.
  elif '--test-launcher-summary-output' in command:
    return GTestTestBinary.from_task_request(task_request)
  elif '--write-run-histories-to=' in command:
    return BlinkWebTestsBinary.from_task_request(task_request)
  raise NotImplementedError('Not Supported test binary: %s' % command)


def create_test_binary_from_jsonish(json_data):
  """Gets test binary object from a jsonish"""
  if not 'class_name' in json_data:
    raise ValueError('Invalid TestBinary json format, missing class_name.')
  if json_data['class_name'] not in TEST_BINARIES:
    raise ValueError('Unknown TestBinary class name: {0}.'.format(
        json_data['class_name']))
  return TEST_BINARIES[json_data['class_name']].from_jsonish(json_data)
