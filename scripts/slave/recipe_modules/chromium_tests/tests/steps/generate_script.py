# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_tests',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
    'test_utils',
]


def RunSteps(api):
  api.gclient.set_config('chromium')
  api.chromium.set_config('chromium')

  update_step = api.bot_update.ensure_checkout()

  single_spec = api.properties.get('single_spec')
  test_spec = {
      'test_buildername': {
          'scripts': [single_spec] if single_spec else [],
      }
  }

  for test in api.chromium_tests._generators.generate_script(
      api,
      api.chromium_tests,
      'test_mastername',
      'test_buildername',
      test_spec,
      update_step,
      scripts_compile_targets={'gtest_test.py': ['$name']}):
    try:
      test.pre_run(api, '')
      test.run(api, '')
    finally:
      api.step('details', [])
      api.step.active_result.presentation.logs['details'] = [
          'compile_targets: %r' % test.compile_targets(),
          'uses_local_devices: %r' % test.uses_local_devices,
      ]


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(
          single_spec={
              'name': 'base_unittests',
              'script': 'gtest_test.py',
          },
          mastername='test_mastername',
          buildername='test_buildername',
          bot_id='test_bot_id',
          buildnumber=123,
      )
  )
