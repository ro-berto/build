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
  api.chromium.set_config('android', TARGET_PLATFORM='android')
  api.chromium_android.set_config('main_builder')

  test = api.chromium_tests.steps.WebViewCTSTest('M', arch='arm64')

  try:
    test.run(api.chromium_tests.m, api.properties['suffix'])
  finally:
    api.step('details', [])
    api.step.active_result.presentation.logs['details'] = [
        'compile_targets: %r' % test.compile_targets(api),
        'uses_local_devices: %r' % test.uses_local_devices,
    ]


def GenTests(api):
  yield (
      api.test('basic pass') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          bot_id='test_bot_id',
          buildnumber=123) +
      api.step_data("Run CTS",
                    api.test_utils.canned_gtest_output(passing=True)) +
      api.properties.generic(suffix='')
  )
  yield (
      api.test('basic fail') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          bot_id='test_bot_id',
          buildnumber=123) +
      api.step_data("Run CTS",
                    api.test_utils.canned_gtest_output(passing=False)) +
      api.properties.generic(suffix='')
  )
  yield (
      api.test('with suffix') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          bot_id='test_bot_id',
          buildnumber=123) +
      api.step_data("Run CTS (build suffix)",
                    api.test_utils.canned_gtest_output(passing=True)) +
      api.properties.generic(suffix='build suffix')
  )
