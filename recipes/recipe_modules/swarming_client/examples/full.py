# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'recipe_engine/properties',
  'recipe_engine/step',
  'swarming_client',
]


def RunSteps(api):
  # Code coverage for these methods.
  result = api.step('client path', [])

  result.presentation.step_text = str(api.swarming_client.path)

  try:
    api.swarming_client.checkout()
  except api.step.StepFailure:
    pass

  _ = api.swarming_client.path


def GenTests(api):
  yield api.test(
      'basic',
      api.properties(parent_got_swarming_client_revision='sample_sha'),
  )

  yield api.test(
      'checkout_error',
      api.properties(parent_got_swarming_client_revision='sample_sha'),
      api.step_data('git checkout (swarming_client)', retcode=1),
  )
