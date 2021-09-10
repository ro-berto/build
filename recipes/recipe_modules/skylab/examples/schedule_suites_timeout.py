# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'recipe_engine/buildbucket',
    'skylab',
]


def RunSteps(api):
  api.skylab.wait_on_suites(1234, timeout_seconds=10)


def GenTests(api):

  def check_step_status(check, steps, expected):
    s = steps['collect skylab results']
    check(s.status == expected)

  # If timeout, 'collect skylab results' step should raise a FAILURE.
  yield api.test(
      'collect_results_failure_by_timeout',
      api.step_data(
          'collect skylab results.buildbucket.collect.wait',
          times_out_after=12),
      api.post_check(check_step_status, 'FAILURE'),
      api.post_process(post_process.DropExpectation),
  )

  # If not timeout, raise an EXCEPTION for whatever failure the collect_build()
  # returned.
  yield api.test(
      'collect_results_exception_by_infra_failure',
      api.step_data(
          'collect skylab results.buildbucket.collect.wait',
          times_out_after=9,
          retcode=1),
      api.post_check(check_step_status, 'EXCEPTION'),
      api.post_process(post_process.DropExpectation),
  )
