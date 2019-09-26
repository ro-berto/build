# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

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
  test_spec = {
      'test_buildername': {
          'junit_tests': [single_spec] if single_spec else [],
      }
  }

  for test in api.chromium_tests._generators.generate_junit_test(
      api,
      api.chromium_tests,
      'test_mastername',
      'test_buildername',
      test_spec,
      update_step):
    test.run(api, '')


def GenTests(api):
  yield api.test(
      'basic',
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123),
      api.properties(
          single_spec={
              'test': 'junit_test',
          },
          mastername='test_mastername',
          bot_id='test_bot_id',
      ),
  )

  yield api.test(
      'different-name',
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123),
      api.properties(
          single_spec={
              'test': 'junit_test',
              'name': 'junit_alias',
          },
          mastername='test_mastername',
          bot_id='test_bot_id',
      ), api.post_process(post_process.MustRun, 'junit_alias'),
      api.override_step_data('junit_alias',
                             api.test_utils.canned_gtest_output(True)),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation))

  yield api.test(
      'additional-args',
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123),
      api.properties(
          single_spec={
              'test': 'junit_test',
              'args': ['--foo=bar'],
          },
          mastername='test_mastername',
          bot_id='test_bot_id',
      ), api.post_process(post_process.MustRun, 'junit_test'),
      api.override_step_data('junit_test',
                             api.test_utils.canned_gtest_output(True)),
      api.post_process(post_process.StepCommandContains, 'junit_test',
                       ['--foo=bar']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation))
