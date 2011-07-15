#!/usr/bin/python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

class TestResult(object):
  """A simple class that represents a single test result."""

  # Test modifier constants.
  (NONE, FAILS, FLAKY, DISABLED) = range(4)

  def __init__(self, test, failed=False, elapsed_time=0):
    self.test_name = test
    self.failed = failed
    self.test_run_time = elapsed_time

    test_name = test
    try:
      test_name = test.split('.')[1]
    except IndexError:
      pass

    if test_name.startswith('FAILS_'):
      self.modifier = self.FAILS
    elif test_name.startswith('FLAKY_'):
      self.modifier = self.FLAKY
    elif test_name.startswith('DISABLED_'):
      self.modifier = self.DISABLED
    else:
      self.modifier = self.NONE

  def fixable(self):
    return self.failed or self.modifier == self.DISABLED
