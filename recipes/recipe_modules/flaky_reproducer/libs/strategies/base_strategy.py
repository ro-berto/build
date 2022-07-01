# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


class BaseStrategy:
  name = 'base'

  TARGET_REPRODUCING_RATE = 0.9
  TARGET_REPRODUCING_TIME_LIMIT = 5 * 60

  def __init__(self, test_binary, result_summary, test_name):
    self.test_binary = test_binary
    self.result_summary = result_summary
    self.test_name = test_name

  def run(self, timeout=45 * 60):
    """Run the strategy logic.

    Returns the best ReproducingStep or None if not reproducible.
    The strategy should finish in [timeout] seconds.
    """
    raise NotImplementedError()
