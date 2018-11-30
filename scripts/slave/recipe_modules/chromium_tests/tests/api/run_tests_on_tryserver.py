# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from recipe_engine import post_process

DEPS = [
    'chromium_tests',
    'recipe_engine/properties',
    'swarming',
    'test_utils',
]


def RunSteps(api):
  bot_config = api.chromium_tests.trybots[
      api.properties['mastername']]['builders'][api.properties['buildername']]
  bot_config_object = api.chromium_tests.create_bot_config_object(
      bot_config['bot_ids'])
  api.chromium_tests.configure_build(bot_config_object)
  update_step, _bot_db = api.chromium_tests.prepare_checkout(bot_config_object)

  if api.properties.get('use_gtest', True):
    kwargs = {}
    if api.properties.get('shards'):
      kwargs['shards'] = api.properties['shards']

    test = api.chromium_tests.steps.SwarmingGTestTest(
        'base_unittests', **kwargs)
  else:
    test = api.chromium_tests.steps.BlinkTest()

  if api.properties.get('disable_retry_with_patch'):
    test._should_retry_with_patch = False

  api.chromium_tests._run_tests_on_tryserver(
      bot_config_object,
      tests=[test],
      bot_update_step=update_step,
      affected_files=api.properties.get('affected_files', []))


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(False))
  )

  retry_with_tests_filter = post_process.Filter().include_re(
      r'.*retry with patch.*')
  yield (
      api.test('enable_retry_with_patch_recipes') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(passing=False)) +
      api.override_step_data(
          'base_unittests (without patch)',
          api.swarming.canned_summary_output(failure=False) +
          api.test_utils.canned_gtest_output(passing=True)) +
      api.post_process(retry_with_tests_filter)
  )

  yield (
      api.test('disable_retry_with_patch_and_deapply') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng',
          disable_retry_with_patch=True,
          affected_files=['testing/buildbot/chromium.linux.json'],
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(passing=False)) +
      api.post_process(post_process.DoesNotRun,
                       'base_unittests (without patch)') +
      api.post_process(post_process.DoesNotRun,
                       'base_unittests (retry with patch)') +
      api.post_process(post_process.StatusFailure) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('disable_retry_with_patch_and_deapply_invalid_results') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng',
          disable_retry_with_patch=True,
          affected_files=['testing/buildbot/chromium.linux.json'],
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.test_utils.canned_isolated_script_output(passing=False,
                                                       valid=False)) +
      api.post_process(post_process.DoesNotRun,
                       'base_unittests (without patch)') +
      api.post_process(post_process.DoesNotRun,
                       'base_unittests (retry with patch)') +
      api.post_process(post_process.StatusFailure) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('disable_retry_with_patch') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng',
          disable_retry_with_patch=True,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(passing=False)) +
      api.override_step_data(
          'base_unittests (without patch)',
          api.swarming.canned_summary_output(failure=False) +
          api.test_utils.canned_gtest_output(passing=True)) +
      api.post_process(post_process.DoesNotRun,
                       'base_unittests (retry with patch)') +
      api.post_process(post_process.StatusFailure) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('enable_retry_with_patch_succeed_after_deapply') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(passing=False)) +
      api.override_step_data(
          'base_unittests (without patch)',
          api.swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(passing=False))
  )


  yield (
      api.test('retry_with_patch_failure') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng',
          use_gtest=False,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'webkit_layout_tests (with patch)',
          api.test_utils.canned_test_output(passing=False)) +
      api.override_step_data(
          'webkit_layout_tests (without patch)',
          api.test_utils.canned_test_output(passing=True)) +
      api.override_step_data(
          'webkit_layout_tests (retry with patch)',
          api.test_utils.canned_test_output(passing=False)) +
      api.post_process(post_process.MustRun,
          'webkit_layout_tests (retry with patch summary)') +
      api.post_process(post_process.AnnotationContains,
          'webkit_layout_tests (retry with patch summary)', ['STEP_FAILURE']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('retry_with_patch_failure_many_shards') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng',
          shards=20,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.swarming.canned_summary_output(failure=True, shards=20) +
          api.test_utils.canned_gtest_output(passing=False)) +
      api.override_step_data(
          'base_unittests (without patch)',
          api.swarming.canned_summary_output(failure=False) +
          api.test_utils.canned_gtest_output(passing=True)) +
      api.override_step_data(
          'base_unittests (retry with patch)',
          api.swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(passing=False)) +
      api.post_process(
          post_process.StepCommandContains,
          'test_pre_run.[trigger] base_unittests (without patch)',
          ['--shards', '6']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('enable_retry_with_patch_invalid_test_results') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(passing=False)) +
      api.override_step_data(
          'base_unittests (without patch)',
          api.swarming.canned_summary_output(failure=False) +
          api.test_utils.canned_gtest_output(passing=True)) +
      api.override_step_data(
          'base_unittests (retry with patch)',
          api.test_utils.canned_isolated_script_output(passing=False,
                                                       valid=False)) +
      api.post_process(retry_with_tests_filter)
  )

  yield (
      api.test('enable_retry_with_patch_invalid_initial_test_results') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.test_utils.canned_isolated_script_output(passing=False,
                                                       valid=False)) +
      api.override_step_data(
          'base_unittests (without patch)',
          api.test_utils.canned_isolated_script_output(passing=False,
                                                       valid=False)) +
      api.override_step_data(
          'base_unittests (retry with patch)',
          api.swarming.canned_summary_output() +
          api.test_utils.canned_gtest_output(passing=True)) +
      api.post_process(post_process.MustRun,
          'test_pre_run.[trigger] base_unittests (retry with patch)') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('enable_retry_with_patch_invalid_without_patch_results') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(passing=False)) +
      api.override_step_data(
          'base_unittests (without patch)',
          api.test_utils.canned_isolated_script_output(passing=False,
                                                       valid=False)) +
      api.override_step_data(
          'base_unittests (retry with patch)',
          api.swarming.canned_summary_output() +
          api.test_utils.canned_gtest_output(passing=True)) +
      api.post_process(post_process.MustRun,
          'test_pre_run.[trigger] base_unittests (retry with patch)') +
      api.post_process(post_process.DropExpectation)
  )

  FAILURE_THEN_SUCCESS_DATA = (
  """
  {
    "per_iteration_data": [
      {
        "Test.One": [{"status": "SUCCESS", "output_snippet": ""}],
        "Test.Two": [
          {"status": "FAILURE", "output_snippet": ""},
          {"status": "SUCCESS", "output_snippet": ""}
        ]
      }
    ]
  }
  """)
  # Any failure in 'retry without patch' should cause the test to be considered
  # flaky on tip of tree, and failures should be ignored.
  yield (
      api.test('retry_without_patch_any_failure') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +

      # canned_gtest_output(passing=False)) marks Test.One as a success,
      # Test.Two as a failure.
      api.override_step_data(
          'base_unittests (with patch)',
          api.swarming.canned_summary_output(failure=False) +
          api.test_utils.canned_gtest_output(passing=False)) +

      # When running the test without patch, it first fails, then succeeds. This
      # indicates that the test is flaky on tip of tree.
      api.override_step_data(
          'base_unittests (without patch)',
          api.swarming.canned_summary_output(failure=False) +
          api.test_utils.gtest_results(FAILURE_THEN_SUCCESS_DATA, retcode=0)) +
      api.post_process(post_process.AnnotationContains,
          'base_unittests (retry summary)', ['ignored']) +
      api.post_process(post_process.AnnotationContains,
          'base_unittests (retry summary)', ['Test.Two']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('disable_deapply_patch_affected_files') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng',
          affected_files=['testing/buildbot/chromium.linux.json'],
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(False))
  )

  yield (
      api.test('nonzero_exit_code_no_gtest_output') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng',
          affected_files=['testing/buildbot/chromium.linux.json'],
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.swarming.canned_summary_output(failure=True) +
          api.test_utils.gtest_results(json.dumps({'per_iteration_data': []}),
                                       retcode=1))
  )
