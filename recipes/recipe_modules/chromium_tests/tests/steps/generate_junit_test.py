# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import generators

DEPS = [
    'chromium',
    'chromium_android',
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
  api.chromium.set_config('chromium', TARGET_PLATFORM='android')
  api.chromium_android.set_config('main_builder')

  update_step = api.bot_update.ensure_checkout()

  single_spec = api.properties.get('single_spec')
  source_side_spec = {
      'test_buildername': {
          'junit_tests': [single_spec] if single_spec else [],
      }
  }

  for test_spec in generators.generate_junit_tests(api, api.chromium_tests,
                                                   'test_group',
                                                   'test_buildername',
                                                   source_side_spec,
                                                   update_step):
    test = test_spec.get_test()
    test.run(api, '')


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(single_spec={
          'test': 'junit_test',
      }),
  )

  yield api.test(
      'different-name',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(single_spec={
          'test': 'junit_test',
          'name': 'junit_alias',
      }),
      api.post_process(post_process.MustRun, 'junit_alias'),
      api.override_step_data('junit_alias',
                             api.test_utils.canned_gtest_output(True)),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'additional-args',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(single_spec={
          'test': 'junit_test',
          'args': ['--foo=bar'],
      }),
      api.post_process(post_process.MustRun, 'junit_test'),
      api.override_step_data('junit_test',
                             api.test_utils.canned_gtest_output(True)),
      api.post_process(post_process.StepCommandContains, 'junit_test',
                       ['--foo=bar']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'junit-with-rdb-by-default',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
          experiments={'chromium.resultdb.result_sink.junit_tests': True},
      ),
      api.properties(single_spec={
          'foo': 'bar',
          'test': 'junit_test',
          'args': ['--foo=bar'],
      }),
      api.post_process(post_process.MustRun, 'junit_test'),
      api.override_step_data('junit_test',
                             api.test_utils.canned_gtest_output(True)),
      api.post_process(post_process.StepCommandContains, 'junit_test', [
          'rdb', 'stream', '-var', 'builder:test_buildername', '-tag',
          'step_name:junit_test', '-coerce-negative-duration', '--'
      ]),
      api.post_process(post_process.StepCommandContains, 'junit_test',
                       ['--foo=bar']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'junit-with-test-spec-rdb-override',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
          experiments={'chromium.resultdb.result_sink.junit_tests': True},
      ),
      api.properties(
          single_spec={
              'foo': 'bar',
              'test': 'junit_test',
              'args': ['--foo=bar'],
              'resultdb': {
                  'enable': True,
                  'test_id_prefix': 'prefix'
              },
          }),
      api.post_process(post_process.MustRun, 'junit_test'),
      api.override_step_data('junit_test',
                             api.test_utils.canned_gtest_output(True)),
      api.post_process(post_process.StepCommandContains, 'junit_test', [
          'rdb', 'stream', '-test-id-prefix', 'prefix', '-var',
          'builder:test_buildername', '-tag', 'step_name:junit_test',
          '-coerce-negative-duration', '--'
      ]),
      api.post_process(post_process.StepCommandContains, 'junit_test',
                       ['--foo=bar']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
