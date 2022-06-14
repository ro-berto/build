# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


class BaseTestBinary:
  """
  The base abstract class for executable TestBinary.

  For the functions marked as optional, you could use cls.support_*() class
  method to check if it's supported by the test suite.
  """

  def run_tests(self, tests, repeat=1):
    """Runs the tests [repeat] times with given [tests]."""
    raise NotImplementedError()
