# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from recipe_engine import post_process
from recipe_engine.recipe_api import Property

DEPS = [
    'chromium_swarming',
    'chromium_tests',
    'recipe_engine/json',
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

  affected_files = api.properties.get('affected_files', [])

  retry_failed_shards = api.properties.get('retry_failed_shards', False)

  # Override _trybot_steps_internal to run the desired test, in the desired
  # configuration.
  def config_override(**kwargs):
    return (bot_config_object, update_step, affected_files, [test],
            retry_failed_shards)
  api.chromium_tests._trybot_steps_internal = config_override

  skip_deapply_patch = api.properties.get(
      'skip_deapply_patch', False)
  if skip_deapply_patch:
    api.chromium_tests._should_retry_with_patch_deapplied = lambda x: False

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
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True))
  )

  yield (
      api.test('test_failures_prevent_cq_retry') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          retry_failed_shards=True,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)) +
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)) +
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(True), failure=False)) +
      api.post_process(post_process.PropertyEquals, 'do_not_retry', True) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('invalid_tests_does_not_prevent_cq_retry') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          retry_failed_shards=True,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      # Initial tests & retry shards with patch produce invalid results.
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(test_results_json='', retcode=1),
              failure=True)) +
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(test_results_json='', retcode=1),
              failure=True)) +
      api.post_process(post_process.PropertiesDoNotContain, 'do_not_retry') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('skip_without_patch_does_not_prevent_cq_retry') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          retry_failed_shards=True,
          skip_deapply_patch=True,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)) +
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)) +
      api.post_process(post_process.PropertiesDoNotContain, 'do_not_retry') +
      api.post_process(post_process.DoesNotRun, '.*without patch.*') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('bot_update_failure_does_not_prevent_cq_retry') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          retry_failed_shards=True,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      # Initial tests & retry shards with patch produce invalid results.
      api.override_step_data('bot_update', retcode=1) +
      api.post_process(post_process.PropertiesDoNotContain, 'do_not_retry') +
      api.post_process(post_process.DropExpectation)
  )

  # TODO(erikchen): Fix this behavior + test once parallel recipe steps has been
  # implemented.
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
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False), failure=True))
          +
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False)))
          +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.StepFailure,
          'base_unittests (with patch)') +
      api.post_process(post_process.DropExpectation)
  )

  # 'retry without ptach' should dispatch higher priority swarming tasks than
  # 'with patch'.
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
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False), failure=False))
          +
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True), failure=False))
          +
      api.post_process(
          post_process.StepCommandContains,
          'test_pre_run (with patch).[trigger] base_unittests (with patch)',
          ['--priority', '30']) +
      api.post_process(
          post_process.StepCommandContains,
          'test_pre_run (without patch).[trigger] base_unittests '
          '(without patch)',
          ['--priority', '29']) +
      api.post_process(post_process.DropExpectation)
  )

  def generate_one_failed_shard_raw():
    shard_zero = api.chromium_swarming.canned_summary_output_raw(
        shard_indices=[0], failure=False)
    shard_one = api.chromium_swarming.canned_summary_output_raw(
        shard_indices=[1], failure=True)
    shards = [shard_zero['shards'][0], shard_one['shards'][0]]
    shards[1]['state'] = 'FAILED'
    return {'shards': shards}

  # If one shard fails or expires, retry shards with patch should retry just
  # that failed/expired shard.
  for failure_type in ['failed', 'expired']:
    test_name = 'retry_shards_with_patch_wait_for_task_' + failure_type

    # This 'with patch' swarming summary contains two shards. First succeeds,
    # second fails.
    swarming_summary = generate_one_failed_shard_raw()
    if failure_type == 'expired':
      swarming_summary['shards'][1]['state'] = 'EXPIRED'
    retry_shards_step_name = (
        'test_pre_run (retry shards with patch).[trigger] base_unittests '
        '(retry shards with patch)')

    # 'retry shards with patch' will only retrigger the second shard. The
    # distinguishing feature is that it has 'custom_task_id' as the task_id.
    retry_trigger_summary = {
      'base_task_name': 'base_task_name_does_not_matter',
      'tasks': {
        'task_name_does_not_matter': {
          'task_id': 'custom_task_id',
          'shard_index': 1,
          'view_url': 'view_url_does_not_matter'
        }
      },
    }

    # When collecting the swarming, make sure to update the task_id of shard 1.
    retry_swarming_summary = dict(swarming_summary)
    retry_swarming_summary['shards'][1]['task_id'] = 'custom_task_id'

    yield (
        api.test(test_name) +
        api.properties.tryserver(
            mastername='tryserver.chromium.linux',
            buildername='linux-rel',
            retry_failed_shards=True,
            shards=2,
            swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
            }) +
        # Override 'with patch' collect step output.
        api.override_step_data(
            'base_unittests (with patch)',
            api.chromium_swarming.summary(
                api.test_utils.canned_gtest_output(passing=False),
                swarming_summary)) +

        # Check that we are sending right input to 'retry shards with patch'
        # trigger.
        api.post_process(post_process.StepCommandContains,
            retry_shards_step_name,
            ['--env', 'GTEST_SHARD_INDEX', '1']) +
        api.post_process(post_process.StepCommandContains,
            retry_shards_step_name,
            ['--env', 'GTEST_TOTAL_SHARDS', '2']) +

        api.post_process(
            post_process.LogContains, retry_shards_step_name, 'json.output',
            ['"shard_index": 1']) +

        # Override 'retry shards with patch' trigger output.
        api.override_step_data(
            retry_shards_step_name,
            api.json.output(retry_trigger_summary)) +

        # Override 'retry shards with patch' collect output.
        api.override_step_data(
            'base_unittests (retry shards with patch)',
            api.chromium_swarming.summary(
                api.test_utils.canned_gtest_output(passing=False),
                retry_swarming_summary)) +

        # We should not emit a link for shard #0, since it wasn't retried.
        api.post_check(lambda check, steps:
            lambda check, steps: 'shard #0'
            not in steps['base_unittests (retry shards with patch)'].links) +

        # We should emit a link for shard#1
        api.post_check(
            lambda check, steps: 'shard #1'
            in steps['base_unittests (retry shards with patch)'].links) +
        api.post_process(post_process.DropExpectation)
    )

  yield (
      api.test('findit_step_layer_flakiness') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          use_gtest=False,
          retry_failed_shards=True,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'blink_web_tests (with patch)',
          api.test_utils.canned_test_output(passing=False)) +
      api.override_step_data(
          'blink_web_tests (without patch)',
          api.test_utils.canned_test_output(passing=True)) +
      api.post_process(
          post_process.LogContains, 'FindIt Flakiness', 'step_metadata',
          ['bad/totally-bad-probably.html', 'blink_web_tests (with patch)']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('findit_step_layer_flakiness_swarming_custom_dimensions') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          use_gtest=True,
          use_custom_dimensions=True,
          retry_failed_shards=True,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch) on Windows-10',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False), failure=True))
          +
      api.override_step_data(
          'base_unittests (retry shards with patch) on Windows-10',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True), failure=False))
          +
      api.post_process(
          post_process.LogContains, 'FindIt Flakiness', 'step_metadata',
          ['base_unittests (with patch) on Windows-10', 'Test.Two']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('findit_step_layer_flakiness_invalid_initial_results') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          retry_failed_shards=True,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(test_results_json='', retcode=1),
              failure=True)) +
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False), failure=True))
          +
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True), failure=False))
          +
      api.post_process(
          post_process.LogContains, 'FindIt Flakiness', 'step_metadata',
          ['Test.Two', 'base_unittests (with patch)']) +
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
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False), failure=True))
          +
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True), failure=False))
          +
      api.post_process(
          post_process.LogContains, 'FindIt Flakiness', 'step_metadata',
          ['Test.Two', 'base_unittests (with patch)']) +
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
      expectations = api.post_process(
          post_process.LogContains, 'FindIt Flakiness', 'step_metadata', [
              '"Step Layer Flakiness": {}',
              'Failing With Patch Tests That Caused Build Failure',
              'base_unittests (with patch)',
              'Test.Two'
          ])
    else:
      expectations = api.post_process(
          post_process.DoesNotRun, 'FindIt Flakiness')

    yield (
        api.test('findit_build_layer_flakiness_' + status) +
        api.properties.tryserver(
            mastername='tryserver.chromium.linux',
            buildername='linux-rel',
            retry_failed_shards=True,
            swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
            }) +
        api.override_step_data(
            'base_unittests (with patch)',
            api.chromium_swarming.canned_summary_output(
               api.test_utils.gtest_results(
                   generate_single_failing_gtest_json(status)),
               retcode=1,
               failure=True)) +
        api.override_step_data(
            'base_unittests (retry shards with patch)',
            api.chromium_swarming.canned_summary_output(
                api.test_utils.canned_gtest_output(passing=False),
                failure=True)) +
        expectations +
        api.post_process(post_process.DropExpectation)
    )

  yield (
      api.test('findit_potential_build_layer_flakiness_skip_retry_with_patch') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False), failure=True))
          +
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True), failure=False))
          +
      api.post_process(
          post_process.LogContains, 'FindIt Flakiness', 'step_metadata', [
              '"Step Layer Flakiness": {}',
              'Failing With Patch Tests That Caused Build Failure',
              'base_unittests (with patch)',
              'Test.Two',
          ]) +
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
      api.test('failure_many_shards') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          shards=20,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  generate_results_for_failure_many_shards(), retcode=1),
              failure=True, shards=20)) +
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True), failure=False))
          +
      api.post_process(
          post_process.StepCommandContains,
          'test_pre_run (without patch)' +
          '.[trigger] base_unittests (without patch)',
          ['--env', 'GTEST_TOTAL_SHARDS', '3']) +
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
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False), failure=False))
          +

      # When running the test without patch, it first fails, then succeeds. This
      # indicates that the test is flaky on tip of tree.
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  FAILURE_THEN_SUCCESS_DATA, retcode=0), failure=False)) +
      api.post_process(
          post_process.StepTextContains, 'base_unittests (retry summary)',
          ['ignored', 'Test.Two']) +
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
          api.chromium_swarming.canned_summary_output(
              api.test_utils.test_results(
                  generate_blink_results('PASS')), failure=False)) +
      api.post_process(post_process.StatusSuccess) +
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
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True))
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
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps({'per_iteration_data': []}),
                  retcode=1), failure=True))
  )

  gtest_results =  {
    'per_iteration_data': [{
      'Test.One': [
        {
          'elapsed_time_ms': 0,
          'output_snippet': '',
          'status': 'FAILURE',
        },
        {
          'elapsed_time_ms': 0,
          'output_snippet': '',
          'status': 'SUCCESS',
        },
      ],
      'Test.Two': [
        {
          'elapsed_time_ms': 0,
          'output_snippet': '',
          'status': 'FAILURE',
        },
        {
          'elapsed_time_ms': 0,
          'output_snippet': '',
          'status': 'FAILURE',
        },
      ],
    }]
  }

  yield (
      api.test('without_patch_only_retries_relevant_tests') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          retry_failed_shards=True,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(gtest_results),
                  retcode=1), failure=True)) +
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(gtest_results),
                  retcode=1), failure=True)) +
      api.post_process(
          post_process.StepCommandContains,
          'test_pre_run (without patch).[trigger] base_unittests '
          '(without patch)', ['--gtest_filter=Test.Two']) +
      api.post_process(post_process.DropExpectation)
  )
