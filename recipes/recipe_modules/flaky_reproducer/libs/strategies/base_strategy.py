# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .reproducing_step import ReproducingStep


class BaseStrategy:
  name = 'base'

  TARGET_REPRODUCING_RATE = 0.9
  TARGET_REPRODUCING_TIME_LIMIT = 5 * 60

  def __init__(self, test_binary, result_summary, test_name):
    self.test_binary = test_binary
    self.result_summary = result_summary
    self.test_name = test_name

  def valid_for_test(self):
    """Verify if the strategy is valid for the given test.

    For example, batch strategy is not valid for a test_binary without batch
    support, or is running tests in 1 batch.
    This method is meant to run in recipe side.
    """
    return True

  def run(self, timeout=45 * 60):
    """Run the strategy logic.

    Returns the best ReproducingStep or None if not reproducible.
    The strategy should finish in [timeout] seconds.
    """
    raise NotImplementedError()

  def _reproducing_step(self, *args, **kwargs):
    """Helper function to embed strategy name in ReproducingStep"""
    kwargs['strategy'] = self.name
    return ReproducingStep(*args, **kwargs)
