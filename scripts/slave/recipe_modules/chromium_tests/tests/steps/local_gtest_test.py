# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_android',
    'chromium_tests',
    'depot_tools/bot_update',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/step',
    'test_results',
    'test_utils',
]


def RunSteps(api):
  api.chromium.set_config(
      'chromium',
      TARGET_PLATFORM=api.properties.get('target_platform', 'linux'))
  api.chromium_android.set_config('main_builder')
  api.test_results.set_config('public_server')

  test = api.chromium_tests.steps.LocalGTestTest('base_unittests')
  assert test.is_gtest and not test.runs_on_swarming

  test_options = api.chromium_tests.steps.TestOptions(
      test_filter=['foo.bar'],
      retry_limit=3,
      run_disabled=True)
  test.test_options = test_options

  try:
    test.run(api, 'with patch')
  finally:
    api.step('details', [])
    api.step.active_result.presentation.logs['details'] = [
        'compile_targets: %r' % test.compile_targets(api),
        'step_metadata: %r' % test.step_metadata(api, ''),
        'pass_fail_counts: %r' % test.pass_fail_counts(api, ''),
        'uses_local_devices: %r' % test.uses_local_devices,
    ]

    test.run(api, 'without patch')


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          bot_id='test_bot_id',
          buildnumber=123)
  )

  yield (
      api.test('retry') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          bot_id='test_bot_id',
          buildnumber=123) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.test_utils.canned_gtest_output(passing=False)) +
      api.override_step_data(
          'base_unittests (without patch)',
          api.test_utils.canned_gtest_output(passing=True))
  )

  yield (
      api.test('android') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          bot_id='test_bot_id',
          buildnumber=123,
          target_platform='android')
  )
