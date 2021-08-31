# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'recipe_engine/assertions',
    'recipe_engine/buildbucket',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'test_results',
    'test_utils',
]

from recipe_engine import post_process
from recipe_engine.recipe_api import Property

from RECIPE_MODULES.build.chromium_tests import steps

# TODO(crbug.com/1135718): Can remove this property and its associated test
# after RDB query logic is re-ordered.
PROPERTIES = {'test_with_new_exit_code': Property(default=None, kind=str)}


def RunSteps(api, test_with_new_exit_code):
  api.chromium.set_config(
      'chromium',
      TARGET_PLATFORM=api.properties.get('target_platform', 'linux'))

  api.chromium_swarming.path_to_merge_scripts = (
      api.path['cache'].join('merge_scripts'))
  api.chromium_swarming.set_default_dimension('pool', 'foo')

  test_specs = [
      steps.SwarmingGTestTestSpec.create(
          'swarming_gtest',
          resultdb=steps.ResultDB(use_rdb_results_for_all_decisions=True)),
      steps.ScriptTestSpec.create(
          'local_script_test',
          script='script.py',
          all_compile_targets={'script.py': 'some_script_target'},
          resultdb=steps.ResultDB(use_rdb_results_for_all_decisions=True)),
      steps.SwarmingIsolatedScriptTestSpec.create(
          'swarming_isolated_script',
          resultdb=steps.ResultDB(use_rdb_results_for_all_decisions=True)),
      steps.LocalIsolatedScriptTestSpec.create(
          'local_isolated_script',
          resultdb=steps.ResultDB(use_rdb_results_for_all_decisions=True)),
      steps.SwarmingIsolatedScriptTestSpec.create(
          'layout_tests',
          resultdb=steps.ResultDB(use_rdb_results_for_all_decisions=True),
          results_handler_name='layout tests'),
  ]
  tests = [ts.get_test() for ts in test_specs]

  invalid_suites, failed_suites = api.test_utils.run_tests(
      api.chromium_tests.m, tests, '')
  for t in tests:
    if t.name == test_with_new_exit_code:
      t.update_failure_on_exit('', True)
    if t.deterministic_failures(''):
      api.step('%s failure' % t.name, cmd=None)
    if not t.has_valid_results(''):
      api.step('%s invalid' % t.name, cmd=None)
    api.assertions.assertEqual(t.failures(''), t.deterministic_failures(''))
    api.assertions.assertFalse(t.pass_fail_counts(''))
    if t.name == test_with_new_exit_code:
      continue  # Can't trust run_tests's return vals if we're changing results.
    if t.deterministic_failures(''):
      api.assertions.assertIn(t, failed_suites)
    elif not t.has_valid_results(''):
      api.assertions.assertIn(t, invalid_suites)
    else:
      api.assertions.assertNotIn(t, failed_suites + invalid_suites)


def GenTests(api):

  def common_test_data():
    return (api.chromium.ci_build(
        builder_group='test_group',
        builder='test_buildername',
        experiments={'chromium.chromium_tests.use_rdb_results': True},
    ) + api.properties(
        swarm_hashes={
            'swarming_gtest': 'gtest-hash',
            'swarming_isolated_script': 'isolated-script-hash',
            'layout_tests': 'layout-test-hash',
        }))

  yield api.test(
      'rdb_success_and_json_success',
      common_test_data(),
      api.override_step_data(
          'swarming_gtest',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(
                  passing=True, use_passthrough_placeholder=True),
              failure=False)),
      api.override_step_data(
          'query test results.swarming_gtest',
          stdout=api.raw_io.output_text(api.test_utils.rdb_results())),
      api.post_process(post_process.DoesNotRun, 'swarming_gtest failure'),
      api.post_process(post_process.DoesNotRun, 'swarming_gtest invalid'),
      api.post_process(post_process.MustRun,
                       'Upload to test-results [swarming_gtest]'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'rdb_success_but_json_failure',
      common_test_data(),
      api.override_step_data(
          'swarming_gtest',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(
                  passing=False, use_passthrough_placeholder=True),
              failure=False)),
      api.override_step_data(
          'query test results.swarming_gtest',
          stdout=api.raw_io.output_text(api.test_utils.rdb_results())),
      api.post_process(post_process.DoesNotRun, 'swarming_gtest failure'),
      api.post_process(post_process.DoesNotRun, 'swarming_gtest invalid'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'rdb_failure_but_json_success',
      common_test_data(),
      api.override_step_data(
          'swarming_gtest',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(
                  passing=True, use_passthrough_placeholder=True),
              failure=False)),
      api.override_step_data(
          'query test results.swarming_gtest',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(failing_suites=['swarming_gtest']))),
      api.post_process(post_process.MustRun, 'swarming_gtest failure'),
      api.post_process(post_process.DoesNotRun, 'swarming_gtest invalid'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'rdb_failure_and_json_failure',
      common_test_data(),
      api.override_step_data(
          'swarming_gtest',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(
                  passing=False, use_passthrough_placeholder=True),
              failure=False)),
      api.override_step_data(
          'query test results.swarming_gtest',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(failing_suites=['swarming_gtest']))),
      api.post_process(post_process.MustRun, 'swarming_gtest failure'),
      api.post_process(post_process.DoesNotRun, 'swarming_gtest invalid'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'rdb_invalid',
      common_test_data(),
      api.override_step_data(
          'swarming_gtest',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(
                  passing=True, use_passthrough_placeholder=True),
              failure=True)),
      api.post_process(post_process.DoesNotRun, 'swarming_gtest failure'),
      api.post_process(post_process.MustRun, 'swarming_gtest invalid'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'rdb_invalid_after_collect',
      common_test_data(),
      api.properties(test_with_new_exit_code='swarming_gtest'),
      api.override_step_data(
          'swarming_gtest',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(
                  passing=True, use_passthrough_placeholder=True),
              failure=False)),
      api.post_process(post_process.DoesNotRun, 'swarming_gtest failure'),
      api.post_process(post_process.MustRun, 'swarming_gtest invalid'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'upload_to_legacy_test_results',
      common_test_data(),
      api.override_step_data(
          'swarming_gtest',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(
                  passing=True, use_passthrough_placeholder=True),
              failure=False)),
      api.post_process(post_process.MustRun,
                       'Upload to test-results [swarming_gtest]'),
      api.post_process(post_process.MustRun,
                       'Upload to test-results [swarming_isolated_script]'),
      api.post_process(post_process.MustRun,
                       'Upload to test-results [layout_tests]'),
      api.post_process(post_process.MustRun,
                       'archive results for layout_tests'),
      api.post_process(post_process.DropExpectation),
  )
