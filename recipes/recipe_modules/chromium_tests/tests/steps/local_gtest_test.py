# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'build',
    'chromium',
    'chromium_android',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/resultdb',
    'recipe_engine/step',
    'test_results',
    'test_utils',
]

from RECIPE_MODULES.build.chromium_tests import steps


def RunSteps(api):
  api.gclient.set_config('chromium')
  api.chromium.set_config(
      'chromium',
      TARGET_PLATFORM=api.properties.get('target_platform', 'linux'))
  api.chromium_android.set_config('main_builder')
  api.test_results.set_config('public_server')
  api.bot_update.ensure_checkout()

  test = steps.LocalGTestTestSpec.create(
      'base_unittests',
      resultdb=steps.ResultDB(enable=True, result_format='gtest'),
  ).get_test()
  assert not test.runs_on_swarming

  test_options = steps.TestOptions(
      test_filter=['foo.bar'], retry_limit=3, run_disabled=True)
  test.test_options = test_options

  try:
    test.run(api, 'with patch')
  finally:
    api.step('details', [])
    api.step.active_result.presentation.logs['details'] = [
        'compile_targets: %r' % test.compile_targets(),
        'step_metadata: %r' % test.step_metadata('with patch'),
        'pass_fail_counts: %r' % test.pass_fail_counts('with patch'),
        'uses_local_devices: %r' % test.uses_local_devices,
    ]

    # Check the pass_fail_counts for a suffix that was not run for
    # coverage
    test.pass_fail_counts('')

    test.run(api, 'without patch')


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(single_spec={
          'test': 'gtest_test',
      },),
  )

  yield api.test(
      'retry',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(single_spec={
          'test': 'gtest_test',
      },),
      api.override_step_data(
          'base_unittests (with patch)',
          api.test_utils.canned_gtest_output(
              passing=False, legacy_annotation=True)),
      api.override_step_data(
          'base_unittests (without patch)',
          api.test_utils.canned_gtest_output(
              passing=True, legacy_annotation=True)),
  )

  yield api.test(
      'windows',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.platform.name('win'),
      api.properties(
          single_spec={'test': 'gtest_test'},
          target_platform='win',
      ),
  )
