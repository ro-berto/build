# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .base_test_binary import (BaseTestBinary, TestBinaryWithBatchMixin,
                               TestBinaryWithParallelMixin)
from .gtest_test_binary import GTestTestBinary

TEST_BINARIES = {
    GTestTestBinary.__name__: GTestTestBinary,
}


def create_test_binary_from_task_request(task_request):
  """Factory method for TestBinary(s) that distinguish and create the correct
  TestBinary object."""
  return GTestTestBinary.from_task_request(task_request)


def create_test_binary_from_jsonish(json_data):
  """Gets test binary object from a jsonish"""
  if not 'class_name' in json_data:
    raise ValueError('Invalid TestBinary json format, missing class_name.')
  if json_data['class_name'] not in TEST_BINARIES:
    raise ValueError('Unknown TestBinary class name: {0}.'.format(
        json_data['class_name']))
  return TEST_BINARIES[json_data['class_name']].from_jsonish(json_data)
