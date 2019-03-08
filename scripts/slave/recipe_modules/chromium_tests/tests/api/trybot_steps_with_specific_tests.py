# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from recipe_engine import post_process
from recipe_engine.recipe_api import Property

DEPS = [
    'chromium_swarming',
    'chromium_tests',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/step',
    'test_utils',
]

PROPERTIES = {
  'mastername': Property(default=None, kind=str),
  'buildername': Property(default=None, kind=str),
}


def RunSteps(api, mastername, buildername):
  trybots = api.chromium_tests.trybots
  bot_config = trybots[mastername]['builders'][buildername]
  bot_config_object = api.chromium_tests.create_bot_config_object(
      bot_config['bot_ids'])

  api.chromium_tests.configure_build(bot_config_object)

  api.chromium_swarming.configure_swarming(
      'chromium', precommit=True,
      # Fake path to make tests pass.
      path_to_testing_dir=api.path['start_dir'].join('checkout'))

  update_step, _bot_db = api.chromium_tests.prepare_checkout(bot_config_object)

  if api.properties.get('use_gtest', True):
    kwargs = {}
    if api.properties.get('shards'):
      kwargs['shards'] = api.properties['shards']

    test = api.chromium_tests.steps.SwarmingGTestTest(
        'base_unittests', **kwargs)
  else:
    test = api.chromium_tests.steps.BlinkTest()

  if api.properties.get('use_custom_dimensions', False):
    api.chromium_swarming.set_default_dimension('os', 'Windows-10')

  if api.properties.get('disable_retry_with_patch'):
    test._should_retry_with_patch = False

  affected_files = api.properties.get('affected_files', [])

  retry_failed_shards = api.properties.get('retry_failed_shards', False)

  # Override _trybot_steps_internal to run the desired test, in the desired
  # configuration.
  def config_override(**kwargs):
    return (bot_config_object, update_step, affected_files, [test],
            retry_failed_shards)
  api.chromium_tests._trybot_steps_internal = config_override

  api.chromium_tests.trybot_steps()


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(False))
  )

  retry_with_tests_filter = post_process.Filter().include_re(
      r'.*retry with patch.*')
  yield (
      api.test('enable_retry_with_patch_recipes') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(passing=False)) +
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(failure=False) +
          api.test_utils.canned_gtest_output(passing=True)) +
      api.post_process(retry_with_tests_filter)
  )

  yield (
      api.test('disable_retry_with_patch_and_deapply') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          disable_retry_with_patch=True,
          affected_files=['testing/buildbot/chromium.linux.json'],
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
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
          buildername='linux-rel',
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
          buildername='linux-rel',
          disable_retry_with_patch=True,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(passing=False)) +
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(failure=False) +
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
          buildername='linux-rel',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(passing=False)) +
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(passing=False)) +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.StepFailure,
          'base_unittests (with patch)') +
      api.post_process(post_process.DropExpectation)
  )

  # If a test fails in 'with patch', it should be marked as a failing step.
  yield (
      api.test('recipe_step_is_failure_for_failing_test') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=False) +
          api.test_utils.canned_gtest_output(passing=False)) +
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(failure=False) +
          api.test_utils.canned_gtest_output(passing=False)) +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.StepFailure,
          'base_unittests (with patch)') +
      api.post_process(post_process.DropExpectation)
  )

  # 'retry with patch' and 'retry without ptach' should dispatch higher priority
  # swarming tasks than 'with patch'.
  yield (
      api.test('retry_swarming_priority') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=False) +
          api.test_utils.canned_gtest_output(passing=False)) +
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(failure=False) +
          api.test_utils.canned_gtest_output(passing=True)) +
      api.override_step_data(
          'base_unittests (retry with patch)',
          api.chromium_swarming.canned_summary_output(failure=False) +
          api.test_utils.canned_gtest_output(passing=True)) +
      api.post_process(
          post_process.StepCommandContains,
          'test_pre_run (with patch).[trigger] base_unittests (with patch)',
          ['--priority', '30']) +
      api.post_process(
          post_process.StepCommandContains,
          'test_pre_run (without patch).[trigger] base_unittests '
          '(without patch)',
          ['--priority', '29']) +
      api.post_process(
          post_process.StepCommandContains,
          'test_pre_run (retry with patch).[trigger] base_unittests '
          '(retry with patch)',
          ['--priority', '29']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('retry_with_patch_failure') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          use_gtest=False,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'blink_web_tests (with patch)',
          api.test_utils.canned_test_output(passing=False)) +
      api.override_step_data(
          'blink_web_tests (without patch)',
          api.test_utils.canned_test_output(passing=True)) +
      api.override_step_data(
          'blink_web_tests (retry with patch)',
          api.test_utils.canned_test_output(passing=False)) +
      api.post_process(post_process.MustRun,
          'blink_web_tests (retry with patch summary)') +
      api.post_process(post_process.AnnotationContains,
          'blink_web_tests (retry with patch summary)', ['STEP_FAILURE']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('findit_step_layer_flakiness') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          use_gtest=False,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'blink_web_tests (with patch)',
          api.test_utils.canned_test_output(passing=False)) +
      api.override_step_data(
          'blink_web_tests (without patch)',
          api.test_utils.canned_test_output(passing=True)) +
      api.override_step_data(
          'blink_web_tests (retry with patch)',
          api.test_utils.canned_test_output(passing=True)) +
      api.post_process(post_process.AnnotationContains,
          'FindIt Flakiness', ['bad/totally-bad-probably.html']) +
      api.post_process(post_process.AnnotationContains,
          'FindIt Flakiness', ['blink_web_tests (with patch)']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('findit_step_layer_flakiness_swarming_custom_dimensions') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          use_gtest=True,
          use_custom_dimensions=True,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch) on Windows-10',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(passing=False)) +
      api.override_step_data(
          'base_unittests (without patch) on Windows-10',
          api.chromium_swarming.canned_summary_output(failure=False) +
          api.test_utils.canned_gtest_output(passing=True)) +
      api.override_step_data(
          'base_unittests (retry with patch) on Windows-10',
          api.chromium_swarming.canned_summary_output(failure=False) +
          api.test_utils.canned_gtest_output(passing=True)) +
      api.post_process(post_process.AnnotationContains,
          'FindIt Flakiness', ['base_unittests (with patch) on Windows-10']) +
      api.post_process(post_process.AnnotationContains,
          'FindIt Flakiness', ['Test.Two']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('findit_step_layer_flakiness_retry_shards') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          retry_failed_shards=True,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(passing=False)) +
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(failure=False) +
          api.test_utils.canned_gtest_output(passing=True)) +
      api.post_process(post_process.AnnotationContains,
          'FindIt Flakiness', ['Test.Two']) +
      api.post_process(post_process.AnnotationContains,
          'FindIt Flakiness', ['base_unittests (with patch)']) +
      api.post_process(post_process.DropExpectation)
  )

  # This tests the following sequence of events:
  # 1) 'with patch' produces invalid results
  # 2) 'retry shards with patch' has a failing test
  # 3) 'without patch' has a passing test.
  # 4) 'retry with patch' has a passing test
  # We expect to have FindIt flakiness metadata emitted for the flaky test,
  # using the 'retry shards with patch' as the name of the failing step.
  yield (
      api.test('findit_step_layer_flakiness_retry_shards_actual_flake') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          retry_failed_shards=True,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.gtest_results('invalid', retcode=1)) +
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(passing=False)) +
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(failure=False) +
          api.test_utils.canned_gtest_output(passing=True)) +
      api.override_step_data(
          'base_unittests (retry with patch)',
          api.chromium_swarming.canned_summary_output(failure=False) +
          api.test_utils.canned_gtest_output(passing=True)) +
      api.post_process(post_process.AnnotationContains,
          'FindIt Flakiness', ['Test.Two']) +
      api.post_process(post_process.AnnotationContains,
          'FindIt Flakiness', ['base_unittests (retry shards with patch)']) +
      api.post_process(post_process.DropExpectation)
  )

  def generate_single_failing_gtest_json(status):
    cur_iteration_data = {
      'Test.Two': [
        {
          'elapsed_time_ms': 0,
          'output_snippet': ':(',
          'status': status,
        },
      ],
    }
    all_iteration_data = {
      'per_iteration_data': [cur_iteration_data]
    }
    return json.dumps(all_iteration_data)

  # A test that fails in 'with patch', and subsequently succeeds in 'retry with
  # patch' should have a FindIt metadata emission. However, if the test fails
  # with 'NOTRUN', then FindIt wants the test to be ignored.
  for status in ['FAILURE', 'NOTRUN']:
    if status == 'FAILURE':
      expectations = (
        api.post_process(post_process.AnnotationContains,
            'FindIt Flakiness', ['"Step Layer Flakiness": {}']) +
        api.post_process(post_process.AnnotationContains,
            'FindIt Flakiness', [
                'Failing With Patch Tests That Caused Build Failure']) +
        api.post_process(post_process.AnnotationContains,
            'FindIt Flakiness', ['base_unittests (with patch)']) +
        api.post_process(post_process.AnnotationContains,
            'FindIt Flakiness', ['Test.Two']))
    else:
      expectations = api.post_process(
          post_process.DoesNotRun, 'FindIt Flakiness')

    yield (
        api.test('findit_build_layer_flakiness_' + status) +
        api.properties.tryserver(
            mastername='tryserver.chromium.linux',
            buildername='linux-rel',
            swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
            }) +
        api.override_step_data(
            'base_unittests (with patch)',
            api.chromium_swarming.canned_summary_output(failure=True) +
            api.test_utils.gtest_results(
                generate_single_failing_gtest_json(status), retcode=1)) +
        api.override_step_data(
            'base_unittests (without patch)',
            api.chromium_swarming.canned_summary_output(failure=False) +
            api.test_utils.canned_gtest_output(passing=True)) +
        api.override_step_data(
            'base_unittests (retry with patch)',
            api.chromium_swarming.canned_summary_output(failure=True) +
            api.test_utils.canned_gtest_output(passing=False)) +
        expectations +
        api.post_process(post_process.DropExpectation)
    )


  yield (
      api.test('findit_potential_build_layer_flakiness_skip_retry_with_patch') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          disable_retry_with_patch=True,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(passing=False)) +
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(failure=False) +
          api.test_utils.canned_gtest_output(passing=True)) +
      api.post_process(post_process.AnnotationContains,
          'FindIt Flakiness', ['"Step Layer Flakiness": {}']) +
      api.post_process(post_process.AnnotationContains,
          'FindIt Flakiness', [
              'Failing With Patch Tests That Caused Build Failure']) +
      api.post_process(post_process.AnnotationContains,
          'FindIt Flakiness', ['base_unittests (with patch)']) +
      api.post_process(post_process.AnnotationContains,
          'FindIt Flakiness', ['Test.Two']) +
      api.post_process(post_process.DropExpectation)
  )

  # To simulate a real test suite, we create results for 100 tests, 3 of
  # which fail. We rerun failing tests 10 times, so the equivalent load is 3*10
  # = 30 tests, which is 30% of the original load of 100 tests. We start with 20
  # shards, so we want 30% * 20 = 6 shards on rerun. However, it doesn't make
  # sense to use more shards than there are tests, so we limit down to 3 shards.
  def generate_results_for_failure_many_shards():
    success_dict = [
          {
            'elapsed_time_ms': 0,
            'output_snippet': ':)',
            'status': 'SUCCESS',
          },
        ]
    failure_dict = [
          {
            'elapsed_time_ms': 0,
            'output_snippet': ':(',
            'status': 'FAILURE'
          },
        ]
    failure_count = 3
    all_results = {}
    for i in xrange(100):
      result_dict = failure_dict if i < failure_count else success_dict
      name = 'Test{}'.format(i)
      all_results[name] = result_dict
    canned_jsonish = {
      'per_iteration_data': [all_results]
    }
    return json.dumps(canned_jsonish)

  yield (
      api.test('retry_with_patch_failure_many_shards') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          shards=20,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=True, shards=20) +
          api.test_utils.gtest_results(
              generate_results_for_failure_many_shards(), retcode=1)) +
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(failure=False) +
          api.test_utils.canned_gtest_output(passing=True)) +
      api.override_step_data(
          'base_unittests (retry with patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(passing=False)) +
      api.post_process(
          post_process.StepCommandContains,
          'test_pre_run (without patch)' +
          '.[trigger] base_unittests (without patch)',
          ['--env', 'GTEST_TOTAL_SHARDS', '3']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('enable_retry_with_patch_invalid_test_results') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(passing=False)) +
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(failure=False) +
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
          buildername='linux-rel',
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
          api.chromium_swarming.canned_summary_output() +
          api.test_utils.canned_gtest_output(passing=True)) +
      api.post_process(
          post_process.MustRun,
          'test_pre_run (retry with patch)' +
          '.[trigger] base_unittests (retry with patch)') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('enable_retry_with_patch_invalid_without_patch_results') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(passing=False)) +
      api.override_step_data(
          'base_unittests (without patch)',
          api.test_utils.canned_isolated_script_output(passing=False,
                                                       valid=False)) +
      api.override_step_data(
          'base_unittests (retry with patch)',
          api.chromium_swarming.canned_summary_output() +
          api.test_utils.canned_gtest_output(passing=True)) +
      api.post_process(
          post_process.MustRun,
          'test_pre_run (retry with patch)' +
          '.[trigger] base_unittests (retry with patch)') +
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
          buildername='linux-rel',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +

      # canned_gtest_output(passing=False)) marks Test.One as a success,
      # Test.Two as a failure.
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=False) +
          api.test_utils.canned_gtest_output(passing=False)) +

      # When running the test without patch, it first fails, then succeeds. This
      # indicates that the test is flaky on tip of tree.
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(failure=False) +
          api.test_utils.gtest_results(FAILURE_THEN_SUCCESS_DATA, retcode=0)) +
      api.post_process(post_process.AnnotationContains,
          'base_unittests (retry summary)', ['ignored']) +
      api.post_process(post_process.AnnotationContains,
          'base_unittests (retry summary)', ['Test.Two']) +
      api.post_process(post_process.DropExpectation)
  )

  # If a test fails, then passes in 'retry with patch', then the build should be
  # marked as a failure. Typically tests are run as multiple iterations, but the
  # behavior should be the same if the test is run multiple times in a single
  # iteration.
  yield (
      api.test('retry_with_patch_failure_then_success_single_iteration') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(passing=False)) +
      api.override_step_data(
          'base_unittests (without patch)',
          api.test_utils.canned_isolated_script_output(passing=True,
                                                       valid=True)) +
      api.override_step_data(
          'base_unittests (retry with patch)',
          api.chromium_swarming.canned_summary_output(failure=False) +
          api.test_utils.gtest_results(FAILURE_THEN_SUCCESS_DATA, retcode=0)) +
      api.post_process(post_process.StatusFailure) +
      api.post_process(post_process.DropExpectation)
  )

  def generate_blink_results(test_output):
    results = {'version': 3}
    results['tests'] = {'random_test_name':{
        'expected':'PASS', 'actual':test_output}}
    return json.dumps(results)

  # This test confirms that generate_blink_results() generates valid results.
  yield (
      api.test('blink_pass') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          use_gtest=False,
          swarm_hashes={
            'blink_web_tests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'blink_web_tests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=False) +
          api.test_utils.gtest_results(generate_blink_results('PASS'))) +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation)
  )

  # If a blink layout test times out, then passes in 'retry with patch', then
  # the build should be marked as a failure.
  yield (
      api.test('retry_with_patch_blink_timeout_then_pass') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          use_gtest=False,
          swarm_hashes={
            'blink_web_tests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'blink_web_tests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=False) +
          api.test_utils.test_results(generate_blink_results('FAIL'))) +
      api.override_step_data(
          'blink_web_tests (without patch)',
          api.chromium_swarming.canned_summary_output(failure=False) +
          api.test_utils.test_results(generate_blink_results('PASS'))) +
      api.override_step_data(
          'blink_web_tests (retry with patch)',
          api.chromium_swarming.canned_summary_output(failure=False) +
          api.test_utils.test_results(generate_blink_results('TIMEOUT PASS'))) +
      api.post_process(post_process.MustRun,
          'blink_web_tests (retry with patch summary)') +
      api.post_process(post_process.AnnotationContains,
          'blink_web_tests (retry with patch summary)', ['STEP_FAILURE']) +
      api.post_process(post_process.StatusFailure) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('disable_deapply_patch_affected_files') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          affected_files=['testing/buildbot/chromium.linux.json'],
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(False))
  )

  yield (
      api.test('nonzero_exit_code_no_gtest_output') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          affected_files=['testing/buildbot/chromium.linux.json'],
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.gtest_results(json.dumps({'per_iteration_data': []}),
                                       retcode=1))
  )
