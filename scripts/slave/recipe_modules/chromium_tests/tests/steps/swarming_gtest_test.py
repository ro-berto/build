# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'code_coverage',
    'depot_tools/bot_update',
    'isolate',
    'recipe_engine/buildbucket',
    'recipe_engine/commit_position',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
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

  # Fake path, as the real one depends on having done a chromium checkout.
  api.code_coverage._merge_scripts_location = api.path['start_dir']

  test = steps.SwarmingGTestTest(
      'base_unittests',
      override_compile_targets=api.properties.get('override_compile_targets'),
      isolate_coverage_data=api.properties.get('isolate_coverage_data', False))

  test_options = steps.TestOptions()
  test.test_options = test_options

  try:
    test.pre_run(api, '')
    test.run(api, '')
    assert test.runs_on_swarming and test.is_gtest
  finally:
    api.step('details', [])
    api.step.active_result.presentation.logs['details'] = [
      'compile_targets: %r' % test.compile_targets(),
      'uses_local_devices: %r' % test.uses_local_devices,
      'uses_isolate: %r' % test.uses_isolate,
      'pass_fail_counts: %r' % test.pass_fail_counts(suffix=''),
    ]



def GenTests(api):

  def verify_log_fields(check, step_odict, expected_fields):
    """Verifies fields in details log are with expected values."""
    step = step_odict['details']
    for field in expected_fields.iteritems():
      expected_log = '%s: %r' % field
      check(expected_log in step.logs['details'])

  yield api.test(
      'basic',
      api.properties(
          mastername='test_mastername',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
      api.override_step_data(
          'base_unittests',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True), failure=False)),
  )

  yield api.test(
      'basic_ignore_task_failure',
      api.properties(
          mastername='test_mastername',
          ignore_task_failure=True,
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
      api.override_step_data(
          'base_unittests',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False),
              failure=False)),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'android',
      api.properties(
          mastername='test_mastername',
          target_platform='android',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
  )

  yield api.test(
      'overrides',
      api.properties(
          override_compile_targets=['base_unittests_run'],
          mastername='test_mastername',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
  )

  yield api.test(
      'no_result_json',
      api.properties(
          mastername='test_mastername',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
      api.override_step_data(
          'base_unittests',
          api.chromium_swarming.canned_summary_output(
              dispatched_task_step_test_data=None, failure=True, retcode=1)),
  )

  yield api.test(
      'invalid_test_result',
      api.properties(
          mastername='test_mastername',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
      api.override_step_data(
          'base_unittests',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(None, 255))),
      api.post_process(verify_log_fields, {'pass_fail_counts': {}}),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'isolate_coverage_data',
      api.properties(
          mastername='test_mastername',
          isolate_coverage_data=True,
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
      api.post_process(post_process.StepCommandContains,
                       '[trigger] base_unittests', [
                           '--env', 'LLVM_PROFILE_FILE',
                           '${ISOLATED_OUTDIR}/profraw/default-%2m.profraw'
                       ]),
      api.post_process(post_process.DropExpectation),
  )
