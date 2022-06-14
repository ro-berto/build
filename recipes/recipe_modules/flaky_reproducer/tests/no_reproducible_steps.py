# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'flaky_reproducer',
    'recipe_engine/step',
    'recipe_engine/assertions',
]


def RunSteps(api):
  # choose_best_reproducing_step should raise StepFailure when no steps.
  api.assertions.assertRaisesRegexp(
      api.step.StepFailure, r'No reproducible step could be found.',
      api.flaky_reproducer.choose_best_reproducing_step, [])


from recipe_engine.post_process import DropExpectation


def GenTests(api):
  yield api.test(
      'full',
      api.post_process(DropExpectation),
  )
