# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import math
import logging
import os
import time

from . import utils
from .base_strategy import BaseStrategy
from .reproducing_step import ReproducingStep
from ..test_binary import TestBinaryWithParallelMixin


class ParallelStrategy(BaseStrategy):
  name = 'parallel'

  MAX_REPEAT = 20
  PARALLEL_JOBS_MULTIPLES = 1.5
  GROUP_VERIFY_TIME_LIMIT = 10 * 60
  SINGLE_TEST_VERIFY_TIME_LIMIT = 5 * 60
  NOT_REPRODUCE_RETRY = 3  # retry up to 3 times if not reproduced.

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.failing_sample = None
    self.deadline = None
    self.parallel_jobs = None
    self.running_time = {}  # test_name: [total_duration, run_cnt]

  def valid_for_test(self):
    if not isinstance(self.test_binary, TestBinaryWithParallelMixin):
      return False
    self.failing_sample = self.result_summary.get_failing_sample(
        self.test_name, default=None)
    if (not self.failing_sample  #
        or not self.failing_sample.start_time or
        self.failing_sample.duration is None):
      return False
    parallel_tests = self._get_parallel_tests()
    if not parallel_tests:
      return False
    return True

  def run(self, timeout=45 * 60):
    self.deadline = (
        time.time() + timeout - self.GROUP_VERIFY_TIME_LIMIT -
        self.SINGLE_TEST_VERIFY_TIME_LIMIT)

    self.failing_sample = self.result_summary.get_failing_sample(
        self.test_name, default=None)
    if (not self.failing_sample  #
        or not self.failing_sample.start_time or
        self.failing_sample.duration is None):
      raise Exception(
          'Parallel strategy requires failing sample with timing info.')
    logging.info('Running %s strategy for %s with reason: %s', self.name,
                 self.test_name, self.failing_sample.primary_error_message)

    parallel_tests = self._get_parallel_tests()
    if not parallel_tests:
      return ReproducingStep(self.test_binary, reproducing_rate=0)
    for test in parallel_tests:
      self.running_time[test.test_name] = [test.duration, 1]
    self.running_time[self.test_name] = [self.failing_sample.duration, 1]

    # Prefer parallel jobs as the number of threads when test fails.
    self.parallel_jobs = len(
        set([x.thread_id for x in parallel_tests]  #
            + [self.failing_sample.thread_id]))
    # Or the current cpu count.
    if self.parallel_jobs <= 1:
      self.parallel_jobs = max(os.cpu_count(), 2)
    # Multiply the parallel jobs to increase the pressure that could improve the
    # reproducing rate.
    self.parallel_jobs = math.floor(self.parallel_jobs *
                                    self.PARALLEL_JOBS_MULTIPLES)

    not_reproduce_retries = self.NOT_REPRODUCE_RETRY
    reproducing_step = None
    while not_reproduce_retries and time.time() < self.deadline:
      reproducing_step = self._find_best_parallel_tests(parallel_tests)
      if reproducing_step:
        return reproducing_step
      not_reproduce_retries -= 1
    return reproducing_step

  def _find_best_parallel_tests(self, tests):
    # Ideally, we want to repeat a group of tests running in parallel while
    # always have the failing test running in another thread. But as that is not
    # supported by test harness.
    # Instead, we would repeat |parallel_jobs| tasks in parallel, which would
    # guarantee a thread runs the failing tests. Plus, we assume the failure
    # just need 1 other test run in parallel to reproduce.

    # Step 1: Verify reproducibility in groups.
    # Group size = parallel_jobs - 1 slot reversed for failing sample.
    groups = [
        tests[i:i + self.parallel_jobs - 1]
        for i in range(0, len(tests), self.parallel_jobs - 1)
    ]
    # We will run each group with failing sample.
    repeat = self._calc_single_round_repeat(
        tests + [self.failing_sample] * len(groups), self.parallel_jobs,
        self.GROUP_VERIFY_TIME_LIMIT)
    # Reproduced results as
    # [(group, reproduced, test_binary, test_history, duration)]
    group_test_results = []
    for i, group in enumerate(groups):
      start_time = time.time()
      reproduced, test_binary, test_history = self._verify_parallel_tests(
          group, repeat)
      duration = time.time() - start_time
      logging.info('verify group %d/%d - reproduced=%d/%d', i, len(groups),
                   reproduced, len(test_history))
      if not reproduced:
        continue
      group_test_results.append(
          (group, reproduced, test_binary, test_history, duration))
    if not group_test_results:
      return ReproducingStep(self.test_binary, reproducing_rate=0)
    best_group_result = max(group_test_results, key=lambda g: g[1])
    best_group = best_group_result[0]

    # Step 2: Verify individual test.
    # We will run each test with failing_sample.
    repeat = self._calc_single_round_repeat(
        best_group + [self.failing_sample] * len(best_group), 2,
        self.SINGLE_TEST_VERIFY_TIME_LIMIT)
    # Reproduced result as
    # [(test, reproduced, test_binary, test_history, duration)]
    single_test_results = []
    for i, test in enumerate(best_group):
      start_time = time.time()
      reproduced, test_binary, test_history = self._verify_parallel_tests(
          [test], repeat)
      duration = time.time() - start_time
      logging.info('verify test %d/%d - reproduced=%d/%d:%s', i,
                   len(best_group), reproduced, len(test_history),
                   ''.join([t.status.name[0] for t in test_history]))
      if not reproduced:
        continue
      single_test_results.append(
          (test, reproduced, test_binary, test_history, duration))
    if not single_test_results:
      return self._generate_reproduce_step(*best_group_result[1:])
    best_single_test_result = max(single_test_results, key=lambda g: g[1])
    return self._generate_reproduce_step(*best_single_test_result[1:])

  def _generate_reproduce_step(self, reproduced, test_binary, test_history,
                               duration):
    duration_per_iteration = duration / len(test_history)
    max_repeat = math.floor(self.TARGET_REPRODUCING_TIME_LIMIT /
                            duration_per_iteration)
    failure_rate = reproduced * 1.0 / len(test_history)
    suggested_repeat = min(
        max_repeat,
        utils.calc_repeat_times_based_on_failing_rate(
            self.TARGET_REPRODUCING_RATE, failure_rate))
    reproducing_rate = 1.0 - (1.0 - failure_rate)**suggested_repeat
    return ReproducingStep(
        test_binary.with_repeat(suggested_repeat),
        reproducing_rate=reproducing_rate,
        duration=duration_per_iteration * suggested_repeat,
        reproduced_cnt=reproduced,
        total_run_cnt=len(test_history))

  def _verify_parallel_tests(self, tests, repeat=None):
    assert self.failing_sample
    if repeat is None:
      time_limit = (
          self.SINGLE_TEST_VERIFY_TIME_LIMIT
          if len(tests) == 1 else self.GROUP_VERIFY_TIME_LIMIT)
      repeat = self._calc_single_round_repeat(tests, len(tests) + 1, time_limit)
    test_history = []
    test_binary = (
        self.test_binary  # go/pyformat-break
        .with_tests([t.test_name for t in tests] + [self.test_name])  #
        .with_parallel_jobs(len(tests) + 1)  #
        .with_repeat(repeat)  #
    )
    result = test_binary.run()
    for test in result:
      if test.duration is None:
        continue
      self.running_time[test.test_name][0] += test.duration
      self.running_time[test.test_name][1] += 1
    test_history = result.get_all(self.test_name)
    if not test_history:
      raise KeyError(
          "Target test wasn't executed during reproducing: {0}".format(
              self.test_name))
    reproduced = 0
    for test in test_history:
      if self.failing_sample.similar_with(test):
        reproduced += 1
    return reproduced, test_binary, test_history

  def _calc_single_round_repeat(self, tests, parallel_jobs, time_limit):
    total_duration = 0
    for test in tests:
      if test.test_name not in self.running_time:
        continue
      duration, cnt = self.running_time[test.test_name]
      total_duration += duration / cnt
    if not total_duration:
      return self.MAX_REPEAT
    repeat = min(
        self.MAX_REPEAT,
        math.floor(time_limit * 1000 / (total_duration / parallel_jobs)))
    return max(repeat, 1)

  def _get_parallel_tests(self):
    """Find tests ran in parallel with failing sample."""
    assert self.failing_sample
    parallel_tests = []
    start_time = self.failing_sample.start_time
    end_time = start_time + self.failing_sample.duration / 1000
    for test in self.result_summary:
      if test is self.failing_sample:
        continue
      if (self.failing_sample.thread_id is not None and
          self.failing_sample.thread_id == test.thread_id):
        continue
      if test.start_time is None or test.duration is None:
        continue
      if (test.start_time <= end_time and
          test.start_time + test.duration / 1000 >= start_time):
        parallel_tests.append(test)
    return sorted(parallel_tests, key=lambda x: x.start_time or 0)
