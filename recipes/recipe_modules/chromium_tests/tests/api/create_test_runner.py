# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.build.chromium_tests import steps

DEPS = [
    'builder_group',
    'chromium',
    'chromium_tests',
    'depot_tools/tryserver',
    'recipe_engine/legacy_annotation',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'test_results',
]


def RunSteps(api):
  api.chromium.set_config('chromium')
  api.chromium_tests.set_config(
      api.properties.get('chromium_tests_config', 'chromium'))
  api.test_results.set_config('public_server')

  test_runner = api.chromium_tests.create_test_runner(
      tests=[steps.LocalGTestTestSpec.create('base_unittests').get_test()],
      serialize_tests=api.properties.get('serialize_tests'),
      retry_failed_shards=api.properties.get('retry_failed_shards'))
  return test_runner()


def GenTests(api):
  yield api.test(
      'failure',
      api.builder_group.for_current('test_group'),
      api.properties(
          buildername='test_buildername', bot_id='test_bot_id',
          buildnumber=123),
      api.override_step_data('base_unittests',
                             api.legacy_annotation.failure_step),
  )

  yield api.test(
      'serialize_tests',
      api.builder_group.for_current('test_group'),
      api.properties(
          buildername='test_buildername',
          bot_id='test_bot_id',
          buildnumber=123,
          serialize_tests=True),
      api.override_step_data('base_unittests',
                             api.legacy_annotation.failure_step),
  )
  yield api.test(
      'retry_failed_shards',
      api.builder_group.for_current('test_group'),
      api.properties(
          buildername='test_buildername',
          bot_id='test_bot_id',
          buildnumber=123,
          retry_failed_shards=True),
      api.override_step_data('base_unittests',
                             api.legacy_annotation.failure_step),
  )
