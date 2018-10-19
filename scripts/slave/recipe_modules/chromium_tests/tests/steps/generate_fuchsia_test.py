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
    'test_results',
    'test_utils',
]


def RunSteps(api):
  api.gclient.set_config('chromium')
  api.chromium.set_config('chromium', TARGET_PLATFORM='fuchsia')
  api.test_results.set_config('staging_server')

  update_step = api.bot_update.ensure_checkout()

  single_spec = api.properties.get('single_spec')
  test_spec = {
      'test_buildername': {
          'gtest_tests': [single_spec] if single_spec else [],
      }
  }

  for test in api.chromium_tests.steps.generate_gtest(
      api,
      api.chromium_tests,
      'test_mastername',
      'test_buildername',
      test_spec,
      update_step):
    test.run(api, '')


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(
          single_spec={
              'test': 'gtest_test',
          },
          mastername='test_mastername',
          buildername='test_buildername',
          bot_id='test_bot_id',
          buildnumber=123,
      )
  )
