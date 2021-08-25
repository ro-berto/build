# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'recipe_engine/step',
  'swarming_client',
]


def RunSteps(api):
  # Code coverage for these methods.
  try:
    api.swarming_client.path
  except api.step.StepFailure:
    pass


def GenTests(api):
  yield api.test(
      'basic',
  )

  yield api.test(
      'checkout_error',
      api.step_data('git checkout (swarming_client)', retcode=1),
  )
