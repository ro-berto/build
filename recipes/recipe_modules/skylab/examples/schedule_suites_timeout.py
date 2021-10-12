# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'skylab',
]


def RunSteps(api):
  api.skylab.wait_on_suites({'foo': 1234}, timeout_seconds=10)


def GenTests(api):

  # If timeout, 'collect skylab results' step should raise an EXCEPTION.
  yield api.test(
      'collect_results_failure_by_timeout',
      api.step_data(
          'collect skylab results.buildbucket.collect.wait',
          times_out_after=12),
      api.post_process(post_process.StepException, 'collect skylab results'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  # If not timeout, raise an EXCEPTION for whatever failure the collect_build()
  # returned.
  yield api.test(
      'collect_results_exception_by_infra_failure',
      api.step_data(
          'collect skylab results.buildbucket.collect.wait',
          retcode=1),
      api.post_process(post_process.StepException, 'collect skylab results'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )
