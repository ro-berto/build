# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.build.chromium_tests import generators

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

from recipe_engine import post_process


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

  for test_spec in generators.generate_script_tests(
      api,
      api.chromium_tests,
      'test_group',
      'test_buildername',
      test_spec,
      update_step,
      scripts_compile_targets_fn=lambda: {'gtest_test.py': ['$name']}):
    test = test_spec.get_test()
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
  yield api.test(
      'basic',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          single_spec={
              'name': 'base_unittests',
              'script': 'gtest_test.py',
          },),
  )

  yield api.test(
      'ci_only_on_ci_builder',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          single_spec={
              'name': 'base_unittests',
              'ci_only': True,
              'script': 'gtest_test.py',
          },),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.MustRun, 'base_unittests'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'ci_only_on_try_builder',
      api.chromium.try_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          single_spec={
              'name': 'base_unittests',
              'ci_only': True,
              'script': 'gtest_test.py',
          },),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DoesNotRun, 'base_unittests'),
      api.post_process(post_process.DropExpectation),
  )
