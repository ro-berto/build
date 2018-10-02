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
  api.chromium.set_config('chromium', TARGET_PLATFORM='android')
  api.chromium_android.set_config('main_builder')

  test = api.chromium_tests.steps.AndroidJunitTest('test_name')

  try:
    test.run(api.chromium_tests.m, '')
  finally:
    assert test.has_valid_results(api.chromium_tests.m, '')
    api.step('details', [])
    api.step.active_result.presentation.logs['details'] = [
        'compile_targets: %r' % test.compile_targets(api.chromium_tests.m),
        'failures: %r' % test.failures(api.chromium_tests.m, ''),
        'uses_local_devices: %r' % test.uses_local_devices,
    ]


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123)
  )
