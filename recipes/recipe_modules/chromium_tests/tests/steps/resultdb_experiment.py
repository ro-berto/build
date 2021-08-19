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

from RECIPE_MODULES.build.chromium_tests import steps


def RunSteps(api):
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
  ]
  tests = [ts.get_test() for ts in test_specs]

  invalid_suites, failed_suites = api.test_utils.run_tests(
      api.chromium_tests.m, tests, '')
  for t in tests:
    if t.deterministic_failures(''):
      api.step('%s failure' % t.name, cmd=None)
    if not t.has_valid_results(''):
      api.step('%s invalid' % t.name, cmd=None)
    api.assertions.assertEqual(t.failures(''), t.deterministic_failures(''))
    api.assertions.assertFalse(t.pass_fail_counts(''))
    if t.deterministic_failures(''):
      api.assertions.assertIn(t, failed_suites)
    elif not t.has_valid_results(''):
      api.assertions.assertIn(t, invalid_suites)
    else:
      api.assertions.assertNotIn(t, failed_suites + invalid_suites)


def GenTests(api):

  yield api.test(
      'rdb_success_and_json_success',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
          experiments={'chromium.chromium_tests.use_rdb_results': True},
      ),
      api.properties(swarm_hashes={
          'swarming_gtest': 'some-hash',
          'swarming_isolated_script': 'some-hash',
      }),
      api.override_step_data(
          'swarming_gtest',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True), failure=False)),
      api.override_step_data(
          'query test results.swarming_gtest',
          stdout=api.raw_io.output_text(api.test_utils.rdb_results())),
      api.post_process(post_process.DoesNotRun, 'swarming_gtest failure'),
      api.post_process(post_process.DoesNotRun, 'swarming_gtest invalid'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'rdb_success_but_json_failure',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
          experiments={'chromium.chromium_tests.use_rdb_results': True},
      ),
      api.properties(swarm_hashes={
          'swarming_gtest': 'some-hash',
          'swarming_isolated_script': 'some-hash',
      }),
      api.override_step_data(
          'swarming_gtest',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False),
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
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
          experiments={'chromium.chromium_tests.use_rdb_results': True},
      ),
      api.properties(swarm_hashes={
          'swarming_gtest': 'some-hash',
          'swarming_isolated_script': 'some-hash',
      }),
      api.override_step_data(
          'swarming_gtest',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True), failure=False)),
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
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
          experiments={'chromium.chromium_tests.use_rdb_results': True},
      ),
      api.properties(swarm_hashes={
          'swarming_gtest': 'some-hash',
          'swarming_isolated_script': 'some-hash',
      }),
      api.override_step_data(
          'swarming_gtest',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False),
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
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
          experiments={'chromium.chromium_tests.use_rdb_results': True},
      ),
      api.properties(swarm_hashes={
          'swarming_gtest': 'some-hash',
          'swarming_isolated_script': 'some-hash',
      }),
      api.override_step_data(
          'swarming_gtest',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True), failure=True)),
      api.post_process(post_process.DoesNotRun, 'swarming_gtest failure'),
      api.post_process(post_process.MustRun, 'swarming_gtest invalid'),
      api.post_process(post_process.DropExpectation),
  )
