# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'recipe_engine/properties',
  'recipe_engine/raw_io',
  'recipe_engine/step',
  'swarming_client',
]


def RunSteps(api):
  # Code coverage for these methods.
  api.step('client path', [])

  with api.swarming_client.on_path():
    api.step('on path', [])

  api.step.active_result.step_text = api.swarming_client.path

  try:
    api.swarming_client.checkout()
  except api.step.StepFailure:
    pass

  api.swarming_client.query_script_version('swarming.py')
  api.swarming_client.ensure_script_version('swarming.py', (0, 4, 4))

  # Coverage for |step_test_data| argument.
  api.swarming_client.query_script_version(
      'isolate.py', step_test_data=(0, 3, 1))

  # 'master' had swarming.py at v0.4.4 at the moment of writing this example.
  assert api.swarming_client.get_script_version('swarming.py') >= (0, 4, 4)

  # Coverage for 'fail' path of ensure_script_version.
  api.swarming_client.ensure_script_version('swarming.py', (20, 0, 0))


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(parent_got_swarming_client_revision='sample_sha') +
      api.step_data(
          'swarming.py --version',
          stdout=api.raw_io.output_text('0.4.4'))
  )

  yield (
      api.test('checkout_error') +
      api.properties(parent_got_swarming_client_revision='sample_sha') +
      api.step_data(
          'git checkout (swarming_client)',
          retcode=1) +
      api.step_data(
          'swarming.py --version',
          stdout=api.raw_io.output_text('0.4.4'))
  )
