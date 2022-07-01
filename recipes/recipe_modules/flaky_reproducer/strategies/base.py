# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


class ReproducingStep:
  """Containing the information needed to reproduce a flaky test failure."""

  def __init__(self,
               test_binary,
               args=None,
               env=None,
               reproduce_rate=0,
               **other):
    self.test_binary = test_binary
    self.args = args or []
    self.env = env or {}
    self.reproduce_rate = reproduce_rate
    self.other_conditions = other

  def readable_info(self):
    """Returns Human readable instruction of the reproducing steps."""
    return 'foobar'


class BaseStrategy:
  name = 'base'

  def __init__(self, test_binary, result_summary, test_name):
    self.test_binary = test_binary
    self.result_summary = result_summary
    self.test_name = test_name

  def run(self, timeout=45 * 60):
    """ Run the strategy logic.

    Returns the best ReproducingStep or None if not reproducible.
    The strategy should finish in [timeout] seconds.
    """
    raise NotImplementedError()
