# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_tests',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
    'test_utils',
]


def RunSteps(api):
  api.gclient.set_config('chromium')

  update_step = api.bot_update.ensure_checkout()

  single_spec = api.properties.get('single_spec')
  test_spec = {
      'test_buildername': {
          'isolated_scripts': [single_spec] if single_spec else [],
      }
  }

  for test in api.chromium_tests.steps.generate_isolated_script(
      api,
      api.chromium_tests,
      'test_mastername',
      'test_buildername',
      test_spec,
      update_step,
      enable_swarming=api.properties.get('enable_swarming')):
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
      api.properties(single_spec={
          'name': 'base_unittests',
          'isolate_name': 'base_unittests_run',
      })
  )

  yield (
      api.test('swarming') +
      api.properties(enable_swarming=True, single_spec={
          'name': 'base_unittests',
          'isolate_name': 'base_unittests_run',
          'merge': {
              'script': '//path/to/script.py',
          },
          'swarming': {
              'can_use_on_swarming_builders': True,
          },
      })
  )

  yield (
      api.test('swarming_dimension_sets') +
      api.properties(enable_swarming=True, single_spec={
          'name': 'base_unittests',
          'isolate_name': 'base_unittests_run',
          'swarming': {
              'can_use_on_swarming_builders': True,
              'dimension_sets': [
                  {'os': 'Linux'},
              ],
          },
      })
  )

  yield (
      api.test('spec_error') +
      api.properties(single_spec={
          'name': 'base_unittests',
          'isolate_name': 'base_unittests_run',
          'results_handler': 'bogus',
      })
  )

  yield (
      api.test('merge_invalid') +
      api.properties(enable_swarming=True, single_spec={
          'name': 'base_unittests',
          'isolate_name': 'base_unittests_run',
          'merge': {
              'script': 'path/to/script.py',
          },
          'swarming': {
              'can_use_on_swarming_builders': True,
          },
      })
  )
