# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .gtest_test_binary import GTestTestBinary


def create_test_binary_from_task_request(task_request):
  """Factory method for TestBinary(s) that distinguish and create the correct
  TestBinary object."""
  return GTestTestBinary.from_task_request(task_request)
