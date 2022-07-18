# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import math
import time

from . import utils
from .base_strategy import BaseStrategy
from .reproducing_step import ReproducingStep


class RepeatStrategy(BaseStrategy):
  name = 'repeat'

  MAX_RETRIES = 1000
  SINGLE_ROUND_RETRIES = 100
  SINGLE_ROUND_SECONDS = 5 * 60

  def run(self, timeout=45 * 60):
    deadline = time.time() + timeout - self.SINGLE_ROUND_SECONDS

    # Reproduces up to 3 times or MAX_RETRIES or reaches the deadline.
    reproduced = 0
    running_history = []
    failing_sample = self.result_summary.get_failing_sample(self.test_name)
    logging.info('Running %s strategy for %s with reason: %s', self.name,
                 self.test_name, failing_sample.primary_error_message)
    single_round_retries = self._calc_single_round_retries()
    while (reproduced < 3 and len(running_history) < self.MAX_RETRIES and
           time.time() < deadline):
      result = (
          self.test_binary  # go/pyformat-break
          .with_tests([self.test_name])  #
          .with_repeat(single_round_retries)  #
      ).run()
      test_history = result.get_all(self.test_name)
      if not test_history:
        raise KeyError(
            "Target test wasn't executed during reproducing: {0}".format(
                self.test_name))
      for r in test_history:
        if failing_sample.similar_with(r):
          reproduced += 1
      running_history += test_history
      single_round_retries = self._calc_single_round_retries(running_history)
    return self._generate_reproducing_step(reproduced, running_history)

  def _calc_single_round_retries(self, running_history=None):
    """Limit the run time of each round within SINGLE_ROUND_SECONDS."""
    if not running_history:
      running_history = self.result_summary.get_all(self.test_name)
    avg_duration = utils.avg_duration(running_history)
    if not avg_duration:
      return self.SINGLE_ROUND_RETRIES
    return math.floor(
        min(self.SINGLE_ROUND_RETRIES,
            self.SINGLE_ROUND_SECONDS * 1000 / avg_duration))

  def _generate_reproducing_step(self, reproduced_cnt, running_history):
    if not running_history:
      raise Exception(
          'Cannot generate reproducing step without running history.')

    # Use minimum 1ms for average duration that the maximum retries equal to the
    # milliseconds of reproducing time limit.
    avg_duration = utils.avg_duration(running_history) or 1
    max_retries = math.ceil(self.TARGET_REPRODUCING_TIME_LIMIT * 1000.0 /
                            avg_duration)
    failure_rate = reproduced_cnt * 1.0 / len(running_history)
    suggested_repeat = min(
        self.MAX_RETRIES, max_retries,
        utils.calc_repeat_times_based_on_failing_rate(
            self.TARGET_REPRODUCING_RATE, failure_rate))
    reproducing_rate = 1.0 - (1.0 - failure_rate)**suggested_repeat
    test_binary = (
        self.test_binary  # go/pyformat-break
        .with_tests([self.test_name])  #
        .with_repeat(suggested_repeat)  #
    )
    return ReproducingStep(
        test_binary,
        reproducing_rate=reproducing_rate,
        duration=avg_duration * suggested_repeat,
        strategy_name=self.name,
        reproduced_cnt=reproduced_cnt,
        total_retries=len(running_history))
