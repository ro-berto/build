# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_android',
    'chromium_tests',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/tryserver',
    'isolate',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
    'swarming',
    'test_results',
    'test_utils',
]


def RunSteps(api):
  api.gclient.set_config('chromium')
  api.chromium.set_config('chromium', TARGET_PLATFORM='android')
  api.chromium_android.set_config('main_builder')

  update_step = api.bot_update.ensure_checkout()

  single_spec = api.properties.get('single_spec')
  test_spec = {
      'test_buildername': {
          'instrumentation_tests': [single_spec] if single_spec else [],
      }
  }

  for test in api.chromium_tests._generators.generate_instrumentation_test(
      api,
      api.chromium_tests,
      'test_mastername',
      'test_buildername',
      test_spec,
      update_step):
    try:
      test.run(api, '')
    finally:
      api.step('details', [])
      api.step.active_result.presentation.logs['details'] = [
          'compile_targets: %r' % test.compile_targets(api),
          'uses_local_devices: %r' % test.uses_local_devices,
      ]


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(
          single_spec={
              'test': 'example_instrumentation_test',
          },
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
      )
  )

  yield (
      api.test('invalid_swarming_dimensions') +
      api.properties(
          single_spec={
              'test': 'example_instrumentation_test',
              'swarming': {
                  'dimension_sets': [{
                      'device_os': 'some_os',
                      'device_type': 'some_device_type'
                  }],
                  'can_use_on_swarming_builders': True
              },
              'precommit_mode': False
          },
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
      )
  )
