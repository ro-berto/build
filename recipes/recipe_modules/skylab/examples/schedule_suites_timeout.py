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

  # If timeout, 'collect skylab results' step should raise an EXCEPTION and
  # not block the following steps.
  yield api.test(
      'collect_results_failure_by_timeout',
      api.step_data(
          'collect skylab results.buildbucket.collect.wait',
          times_out_after=12),
      api.post_process(post_process.StepException, 'collect skylab results'),
      api.post_process(post_process.MustRun, 'find test runner build'),
      api.post_process(post_process.DropExpectation),
  )
