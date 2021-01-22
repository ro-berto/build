# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from google.protobuf import json_format

from recipe_engine import post_process
from recipe_engine.recipe_api import Property

from PB.recipe_engine import result as result_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb

from PB.go.chromium.org.luci.resultdb.proto.v1 import (invocation as
                                                       invocation_pb2)
from PB.go.chromium.org.luci.resultdb.proto.v1 import (test_result as
                                                       test_result_pb2)

from RECIPE_MODULES.build.chromium_tests import steps

DEPS = [
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'depot_tools/tryserver',
    'recipe_engine/assertions',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/resultdb',
    'recipe_engine/step',
    'recipe_engine/swarming',
    'test_utils',
]

PROPERTIES = {
    'fail_calculate_tests': Property(default=False, kind=bool),
    'fail_mb_and_compile': Property(default=False, kind=bool),
    'expected_jsonish_result': Property(default=None),
}


def RunSteps(api, fail_calculate_tests, fail_mb_and_compile,
             expected_jsonish_result):
  assert api.tryserver.is_tryserver
  bot = api.chromium_tests.lookup_bot_metadata(builders={})

  api.chromium_tests.configure_build(bot.settings)
  api.chromium_swarming.configure_swarming(
      'chromium',
      precommit=True,
      # Fake path to make tests pass.
      path_to_merge_scripts=api.path['start_dir'].join('checkout',
                                                       'merge_scripts'))

  update_step, _build_config = api.chromium_tests.prepare_checkout(bot.settings)

  kwargs = {}
  if api.properties.get('shards'):
    kwargs['shards'] = api.properties['shards']

  test_specs = [steps.SwarmingGTestTestSpec.create('base_unittests', **kwargs)]

  if api.properties.get('use_custom_dimensions', False):
    api.chromium_swarming.set_default_dimension('os', 'Windows-10')

  affected_files = api.properties.get('affected_files', [])

  retry_failed_shards = api.properties.get('retry_failed_shards', False)

  # Allows testing the scenario where there are multiple test suites.
  for t in api.properties.get('additional_gtest_targets', []):
    test_specs.append(steps.SwarmingGTestTestSpec.create(t))

  tests = [s.get_test() for s in test_specs]

  # Override _calculate_tests_to_run to run the desired test, in the desired
  # configuration.
  def config_override(**kwargs):
    task = api.chromium_tests.Task(bot, tests, update_step, affected_files)
    task.should_retry_failures_with_changes = lambda: retry_failed_shards
    raw_result = result_pb2.RawResult(status=common_pb.SUCCESS)
    if fail_calculate_tests:
      raw_result.summary_markdown = (
          'Compile step failed from "_calculate_tests_to_run".')
      raw_result.status = common_pb.FAILURE
    return raw_result, task

  api.chromium_tests._calculate_tests_to_run = config_override

  def compile_override(*args, **kwargs):
    return result_pb2.RawResult(
        status=common_pb.FAILURE,
        summary_markdown='Compile step failed from "run_mb_and_compile".'
    )

  if fail_mb_and_compile:
    api.chromium_tests.run_mb_and_compile = compile_override

  skip_deapply_patch = api.properties.get(
      'skip_deapply_patch', False)
  if skip_deapply_patch:
    api.chromium_tests._should_retry_with_patch_deapplied = lambda x: False

  result = api.chromium_tests.trybot_steps()
  if expected_jsonish_result is not None:
    api.assertions.assertDictEqual(
        expected_jsonish_result, json.loads(json_format.MessageToJson(result)))

  return result


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(swarm_hashes={
          'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
      }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
  )

  yield api.test(
      'calculate_tests_compile_failure',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(fail_calculate_tests=True),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.ResultReason,
                       'Compile step failed from "_calculate_tests_to_run".'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'run_mb_and_compile_failure',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          fail_mb_and_compile=True,
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.ResultReason,
                       'Compile step failed from "run_mb_and_compile".'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'test_failures_prevent_cq_retry',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          retry_failed_shards=True,
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(True), failure=False)),
      api.post_process(post_process.PropertyEquals, 'do_not_retry', True),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'invalid_tests_does_not_prevent_cq_retry',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          retry_failed_shards=True,
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      # Initial tests & retry shards with patch produce invalid results.
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(test_results_json='', retcode=1),
              failure=True)),
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(test_results_json='', retcode=1),
              failure=True)),
      api.post_process(post_process.PropertiesDoNotContain, 'do_not_retry'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'skip_without_patch_does_not_prevent_cq_retry',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          retry_failed_shards=True,
          skip_deapply_patch=True,
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.post_process(post_process.PropertiesDoNotContain, 'do_not_retry'),
      api.post_process(post_process.DoesNotRun, '.*without patch.*'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'bot_update_failure_does_not_prevent_cq_retry',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          retry_failed_shards=True,
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      # Initial tests & retry shards with patch produce invalid results.
      api.override_step_data('bot_update', retcode=1),
      api.post_process(post_process.PropertiesDoNotContain, 'do_not_retry'),
      api.post_process(post_process.DropExpectation),
  )

  # TODO(erikchen): Fix this behavior + test once parallel recipe steps has been
  # implemented.
  # If a test fails in 'with patch', it should be marked as a failing step.
  yield api.test(
      'recipe_step_is_failure_for_failing_test',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(swarm_hashes={
          'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
      }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False), failure=True)),
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False))),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.StepFailure, 'base_unittests (with patch)'),
      api.post_process(post_process.DropExpectation),
  )

  # 'retry without ptach' should dispatch higher priority swarming tasks than
  # 'with patch'.
  yield api.test(
      'retry_swarming_priority',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(swarm_hashes={
          'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
      }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False),
              failure=False)),
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True), failure=False)),
      api.post_check(
          api.swarming.check_triggered_request,
          'test_pre_run (with patch).[trigger] base_unittests (with patch)',
          lambda check, req: check(req.priority == 30)),
      api.post_check(
          api.swarming.check_triggered_request,
          'test_pre_run (without patch).[trigger] base_unittests ' +
          '(without patch)', lambda check, req: check(req.priority == 29)),
      api.post_process(post_process.DropExpectation),
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
        'tasks': [{
            'task_id': 'custom_task_id',
            'request': {
                'name': 'task_name_does_not_matter',
            },
            'task_result': {
                'resultdb_info': {
                    'invocation': 'invocations/custom_task_id',
                }
            },
        },]
    }

    # When collecting the swarming, make sure to update the task_id of shard 1.
    retry_swarming_summary = dict(swarming_summary)
    retry_swarming_summary['shards'][1]['task_id'] = 'custom_task_id'

    base_unittests_retry = 'base_unittests (retry shards with patch)'

    def check_gtest_shrad_env(check, req):
      check(req[0].env_vars['GTEST_SHARD_INDEX'] == '1')
      check(req[0].env_vars['GTEST_TOTAL_SHARDS'] == '2')

    yield api.test(
        test_name,
        api.chromium.try_build(
            builder_group='tryserver.chromium.linux',
            builder='linux-rel'),
        api.properties(
            retry_failed_shards=True,
            shards=2,
            swarm_hashes={
                'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
            }),
        # Override 'with patch' collect step output.
        api.override_step_data(
            'base_unittests (with patch)',
            api.chromium_swarming.summary(
                api.test_utils.canned_gtest_output(passing=False),
                swarming_summary)),

        # Check that we are sending right input to 'retry shards with patch'
        # trigger.
        api.post_process(post_process.LogContains, retry_shards_step_name,
                         'json.output', ['"task_id": "custom_task_id"']),
        api.post_check(api.swarming.check_triggered_request,
          retry_shards_step_name, check_gtest_shrad_env),


        # Override 'retry shards with patch' trigger output.
        api.override_step_data(retry_shards_step_name,
                               api.json.output(retry_trigger_summary)),

        # Override 'retry shards with patch' collect output.
        api.override_step_data(
            'base_unittests (retry shards with patch)',
            api.chromium_swarming.summary(
                api.test_utils.canned_gtest_output(passing=False),
                retry_swarming_summary)),

        # We should not emit a link for shard #0, since it wasn't retried.
        api.post_check(
            # Line is too long, but yapf won't break it, so backslash
            # continuation
            # https://github.com/google/yapf/issues/763
            lambda check, steps: \
            'shard #0' not in steps[base_unittests_retry].links
        ),

        # We should emit a link for shard#1
        api.post_check(
            lambda check, steps: 'shard #1' in steps[base_unittests_retry].links
        ),
        api.post_process(post_process.DropExpectation),
    )

  expected_findit_metadata = {
      'Failing With Patch Tests That Caused Build Failure': {},
      'Step Layer Flakiness': {
          'base_unittests (with patch) on Windows-10': ['Test.Two',],
      },
      'Step Layer Skipped Known Flakiness': {},
  }
  yield api.test(
      'findit_step_layer_flakiness_swarming_custom_dimensions',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          use_custom_dimensions=True,
          retry_failed_shards=True,
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.override_step_data(
          'base_unittests (with patch) on Windows-10',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False), failure=True)),
      api.override_step_data(
          'base_unittests (retry shards with patch) on Windows-10',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True), failure=False)),
      api.post_process(
          post_process.LogEquals, 'FindIt Flakiness', 'step_metadata',
          json.dumps(expected_findit_metadata, sort_keys=True, indent=2)),
      api.post_process(post_process.DropExpectation),
  )

  expected_findit_metadata = {
      'Failing With Patch Tests That Caused Build Failure': {
          'base_unittests (with patch)': ['Test.Two'],
      },
      'Step Layer Flakiness': {},
      'Step Layer Skipped Known Flakiness': {},
  }
  yield api.test(
      'findit_step_layer_flakiness_invalid_initial_results',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          retry_failed_shards=True,
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(test_results_json='', retcode=1),
              failure=True)),
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False), failure=True)),
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True), failure=False)),
      api.post_process(
          post_process.LogEquals, 'FindIt Flakiness', 'step_metadata',
          json.dumps(expected_findit_metadata, sort_keys=True, indent=2)),
      api.post_process(post_process.DropExpectation),
  )

  with_patch_gtest_results = {
      'per_iteration_data': [{
          'Test.One': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'FAILURE',
          }, {
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'FAILURE',
          }],
      }]
  }
  retry_shards_with_patch_gtest_results = {
      'per_iteration_data': [{
          'Test.One': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'FAILURE',
          }, {
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'SUCCESS',
          }],
      }]
  }
  expected_findit_metadata = {
      'Failing With Patch Tests That Caused Build Failure': {},
      'Step Layer Flakiness': {
          'base_unittests (with patch)': ['Test.One'],
      },
      'Step Layer Skipped Known Flakiness': {},
  }
  # This test tests the scenario when a test failed deterministically with patch
  # (FAILURE, FAILURE), but then passed retry shards with patch in a flaky way
  # (FAILURE, SUCCESS), the test is expected to be labeled as
  # "Step Layer Flakiness".
  yield api.test(
      'findit_step_layer_flakiness_retry_shards_flaky_test',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          retry_failed_shards=True,
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(with_patch_gtest_results), retcode=1),
              failure=True)),
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(retry_shards_with_patch_gtest_results), retcode=1),
              failure=True)),
      api.post_process(
          post_process.LogEquals, 'FindIt Flakiness', 'step_metadata',
          json.dumps(expected_findit_metadata, sort_keys=True, indent=2)),
      api.post_process(post_process.DropExpectation),
  )


  expected_findit_metadata = {
      'Failing With Patch Tests That Caused Build Failure': {},
      'Step Layer Flakiness': {
          'base_unittests (with patch)': ['Test.Two'],
      },
      'Step Layer Skipped Known Flakiness': {},
  }
  yield api.test(
      'findit_step_layer_flakiness_retry_shards',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          retry_failed_shards=True,
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False), failure=True)),
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True), failure=False)),
      api.post_process(
          post_process.LogEquals, 'FindIt Flakiness', 'step_metadata',
          json.dumps(expected_findit_metadata, sort_keys=True, indent=2)),
      api.post_process(post_process.DropExpectation),
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

    yield api.test(
        'findit_build_layer_flakiness_' + status,
        api.chromium.try_build(
            builder_group='tryserver.chromium.linux', builder='linux-rel'),
        api.properties(
            retry_failed_shards=True,
            swarm_hashes={
                'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
            }),
        api.override_step_data(
            'base_unittests (with patch)',
            api.chromium_swarming.canned_summary_output(
                api.test_utils.gtest_results(
                    generate_single_failing_gtest_json(status)),
                retcode=1,
                failure=True)),
        api.override_step_data(
            'base_unittests (retry shards with patch)',
            api.chromium_swarming.canned_summary_output(
                api.test_utils.canned_gtest_output(passing=False),
                failure=True)),
        expectations,
        api.post_process(post_process.DropExpectation),
    )

  expected_findit_metadata = {
      'Failing With Patch Tests That Caused Build Failure': {
          'base_unittests (with patch)': ['Test.Two'],
      },
      'Step Layer Flakiness': {},
      'Step Layer Skipped Known Flakiness': {},
  }
  yield api.test(
      'findit_potential_build_layer_flakiness_skip_retry_with_patch',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(swarm_hashes={
          'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
      }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False), failure=True)),
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True), failure=False)),
      api.post_process(
          post_process.LogEquals, 'FindIt Flakiness', 'step_metadata',
          json.dumps(expected_findit_metadata, sort_keys=True, indent=2)),
      api.post_process(post_process.DropExpectation),
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

  yield api.test(
      'failure_many_shards',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          shards=20,
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  generate_results_for_failure_many_shards(), retcode=1),
              failure=True,
              shards=20)),
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True), failure=False)),
      api.post_check(
          api.swarming.check_triggered_request, 'test_pre_run (without patch)' +
          '.[trigger] base_unittests (without patch)', lambda check, req: check(
              req[0].env_vars['GTEST_TOTAL_SHARDS'] == '3')),
      api.post_process(post_process.DropExpectation),
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
  yield api.test(
      'retry_without_patch_any_failure',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(swarm_hashes={
          'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
      }),

      # canned_gtest_output(passing=False)) marks Test.One as a success,
      # Test.Two as a failure.
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False),
              failure=False)),

      # When running the test without patch, it first fails, then succeeds. This
      # indicates that the test is flaky on tip of tree.
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  FAILURE_THEN_SUCCESS_DATA, retcode=0),
              failure=False)),
      api.post_process(post_process.StepTextContains,
                       'base_unittests (test results summary)',
                       ['ignored', 'Test.Two']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'disable_deapply_patch_affected_files',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          affected_files=['testing/buildbot/chromium.linux.json'],
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
  )

  yield api.test(
      'nonzero_exit_code_no_gtest_output',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          affected_files=['testing/buildbot/chromium.linux.json'],
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps({'per_iteration_data': []}), retcode=1),
              failure=True)),
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

  yield api.test(
      'without_patch_only_retries_relevant_tests',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          retry_failed_shards=True,
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(gtest_results), retcode=1),
              failure=True)),
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(gtest_results), retcode=1),
              failure=True)),
      api.post_check(
          api.swarming.check_triggered_request,
          'test_pre_run (without patch).[trigger] base_unittests '
          '(without patch)', lambda check, req: check('--gtest_filter=Test.Two'
                                                      in req[0].command)),
      api.post_process(post_process.DropExpectation),
  )



  with_patch_gtest_results = {
      'per_iteration_data': [{
          'Test.One': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'FAILURE',
          },],
          'Test.Two': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'FAILURE',
          },],
          'Test.Three': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'FAILURE',
          },],
      }]
  }

  retry_shards_with_patch_gtest_results = {
      'per_iteration_data': [{
          'Test.One': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'FAILURE',
          },],
          'Test.Two': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'SUCCESS',
          },],
          'Test.Three': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'FAILURE',
          },],
      }]
  }

  without_patch_gtest_results = {
      'per_iteration_data': [{
          'Test.One': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'SUCCESS',
          },],
          'Test.Three': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'FAILURE',
          },],
      }]
  }

  # This test tests that only Test.One is determined as unrecoverable failures
  # presented to the users because Test.Two is ignored by
  # "retry shards with patch" and "Test.Three" is ignored by "without patch".
  yield api.test(
      'unrecoverable_failure_results_exclude_ignored_failures',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          retry_failed_shards=True,
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          expected_jsonish_result={
              'status':
                  'FAILURE',
              'summaryMarkdown':
                  ('1 Test Suite(s) failed.\n\n**base_unittests** failed '
                   'because of:\n\n- Test.One'),
          }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(with_patch_gtest_results), retcode=1),
              failure=True)),
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(retry_shards_with_patch_gtest_results), retcode=1),
              failure=True)),
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(without_patch_gtest_results), retcode=1),
              failure=True)),
      api.post_process(post_process.DropExpectation),
  )


  expected_findit_metadata = {
      'Failing With Patch Tests That Caused Build Failure': {},
      'Step Layer Flakiness': {},
      'Step Layer Skipped Known Flakiness': {
          'base_unittests (with patch)': ['Test.Two'],
      },
  }
  yield api.test(
      'succeeded_to_exonerate_flaky_failures',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          retry_failed_shards=True,
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.step_data(
          'query known flaky failures on CQ',
          api.json.output({
              'flakes': [{
                  'test': {
                      'step_ui_name': 'base_unittests (with patch)',
                      'test_name': 'Test.Two',
                  },
                  'affected_gerrit_changes': ['123', '234'],
                  'monorail_issue': '999',
              }]
          })),
      api.post_process(post_process.MustRun, 'base_unittests (with patch)'),
      api.post_process(post_process.DoesNotRun,
                       'base_unittests (retry shards with patch)'),
      api.post_process(post_process.DoesNotRun,
                       'base_unittests (without patch)'),
      api.post_process(
          post_process.StepTextContains,
          'base_unittests (test results summary)', [
              'Tests failed with patch, but ignored as they are known to be '
              'flaky:<br/>Test.Two: crbug.com/999<br/>'
          ]),
      api.post_process(
          post_process.LogEquals, 'FindIt Flakiness', 'step_metadata',
          json.dumps(expected_findit_metadata, sort_keys=True, indent=2)),
      api.post_process(post_process.DropExpectation),
  )

  expected_findit_metadata = {
      'Failing With Patch Tests That Caused Build Failure': {
          'base_unittests (with patch)': ['Test.Two'],
      },
      'Step Layer Flakiness': {},
      'Step Layer Skipped Known Flakiness': {},
  }
  yield api.test(
      'failed_to_exonerate_flaky_failures',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          retry_failed_shards=True,
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.step_data('query known flaky failures on CQ', api.json.output([])),
      api.post_process(post_process.MustRun, 'base_unittests (with patch)'),
      api.post_process(post_process.MustRun,
                       'base_unittests (retry shards with patch)'),
      api.post_process(post_process.MustRun, 'base_unittests (without patch)'),
      api.post_process(
          post_process.StepTextContains,
          'base_unittests (test results summary)', [
              'Tests failed with patch, and caused build to fail:<br/>'
              'Test.Two<br/>'
          ]),
      api.post_process(
          post_process.LogEquals, 'FindIt Flakiness', 'step_metadata',
          json.dumps(expected_findit_metadata, sort_keys=True, indent=2)),
      api.post_process(post_process.DropExpectation),
  )

  with_patch_gtest_results = {
      'per_iteration_data': [{
          'Test.One': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'FAILURE',
          },],
          'Test.Two': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'FAILURE',
          },],
      }]
  }

  retry_shards_with_patch_gtest_results = {
      'per_iteration_data': [{
          'Test.One': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'SUCCESS',
          },],
          'Test.Two': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'FAILURE',
          },],
      }]
  }

  expected_findit_metadata = {
      'Failing With Patch Tests That Caused Build Failure': {},
      'Step Layer Flakiness': {
          'base_unittests (with patch)': ['Test.One'],
      },
      'Step Layer Skipped Known Flakiness': {
          'base_unittests (with patch)': ['Test.Two'],
      },
  }

  # This test tests the scenario that if a known flaky failure fails again while
  # retrying, it doesn't fail a test suite as long as there are no other
  # non-flaky failures. For example: t1 and t2 failed "with patch", and t2 is
  # known to be flaky, while retrying, t1 succeeds but t2 fails again, and the
  # build is expected to be succeed without running "without patch" steps.
  yield api.test(
      'known_flaky_failure_failed_again_while_retrying',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          retry_failed_shards=True,
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(with_patch_gtest_results), retcode=1),
              failure=True)),
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(retry_shards_with_patch_gtest_results), retcode=1),
              failure=True)),
      api.step_data(
          'query known flaky failures on CQ',
          api.json.output({
              'flakes': [{
                  'test': {
                      'step_ui_name': 'base_unittests (with patch)',
                      'test_name': 'Test.Two',
                  },
                  'affected_gerrit_changes': ['123', '234'],
                  'monorail_issue': '999',
              }]
          })),
      api.post_process(post_process.MustRun, 'base_unittests (with patch)'),
      api.post_process(post_process.MustRun,
                       'base_unittests (retry shards with patch)'),
      api.post_process(post_process.DoesNotRun,
                       'base_unittests (without patch)'),
      api.post_process(
          post_process.StepTextContains,
          'base_unittests (test results summary)', [
              'Tests failed with patch, but ignored as they are known to be '
              'flaky:<br/>Test.Two: crbug.com/999<br/>'
          ]),
      api.post_process(
          post_process.LogEquals, 'FindIt Flakiness', 'step_metadata',
          json.dumps(expected_findit_metadata, sort_keys=True, indent=2)),
      api.post_process(post_process.DropExpectation),
  )

  with_patch_gtest_results = {
      'per_iteration_data': [{
          'Test.One': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'FAILURE',
          },],
          'Test.Two': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'FAILURE',
          },],
      }]
  }

  retry_shards_with_patch_gtest_results = {
      'per_iteration_data': [{
          'Test.One': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'FAILURE',
          },],
          'Test.Two': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'FAILURE',
          },],
      }]
  }

  expected_findit_metadata = {
      'Failing With Patch Tests That Caused Build Failure': {
          'base_unittests (with patch)': ['Test.One'],
      },
      'Step Layer Flakiness': {},
      'Step Layer Skipped Known Flakiness': {
          'base_unittests (with patch)': ['Test.Two'],
      },
  }

  # This test tests the scenario that a known flaky failure shouldn't be retried
  # "without patch". For example: t1 and t2 failed "with patch", and t2 is
  # known to be flaky, while retrying, t1 and t2 fails again, and only t1 is
  # expected to be retried during "without patch".
  yield api.test(
      'without_patch_only_retries_non_flaky_failures',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          retry_failed_shards=True,
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(with_patch_gtest_results), retcode=1),
              failure=True)),
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(retry_shards_with_patch_gtest_results), retcode=1),
              failure=True)),
      api.step_data(
          'query known flaky failures on CQ',
          api.json.output({
              'flakes': [{
                  'test': {
                      'step_ui_name': 'base_unittests (with patch)',
                      'test_name': 'Test.Two',
                  },
                  'affected_gerrit_changes': ['123', '234'],
                  'monorail_issue': '999',
              }]
          })),
      api.post_process(post_process.MustRun, 'base_unittests (with patch)'),
      api.post_process(post_process.MustRun,
                       'base_unittests (retry shards with patch)'),
      api.post_process(post_process.MustRun, 'base_unittests (without patch)'),
      api.post_check(
          api.swarming.check_triggered_request,
          'test_pre_run (without patch).[trigger] base_unittests '
          '(without patch)', lambda check, req: check('--gtest_filter=Test.One'
                                                      in req[0].command)),
      api.post_process(
          post_process.StepTextContains,
          'base_unittests (test results summary)', [
              'Tests failed with patch, and caused build to fail:'
              '<br/>Test.One<br/>',
              'Tests failed with patch, but ignored as they are known to be '
              'flaky:<br/>Test.Two: crbug.com/999<br/>'
          ]),
      api.post_process(
          post_process.LogEquals, 'FindIt Flakiness', 'step_metadata',
          json.dumps(expected_findit_metadata, sort_keys=True, indent=2)),
      api.post_process(post_process.DropExpectation),
  )

  base_unittests_results = {
      'per_iteration_data': [{
          'BaseTest.One': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'FAILURE',
          },],
      }]
  }

  url_unittests_results = {
      'per_iteration_data': [{
          'UrlTest.One': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'FAILURE',
          },],
      }]
  }

  url_unittests_retry_shards_results = {
      'per_iteration_data': [{
          'UrlTest.One': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'FAILURE',
          },],
      }]
  }

  # This test tests the scenrio when there are multiple test suites with
  # failures and that after the "without patch" steps, there are two different
  # kinds test suites need to summarize their results:
  # 1. Those ran "without patch" steps because there are non-forgivable failures
  #    after "with patch" steps.
  # 2. Those didn't run "without patch" steps because their failures are known
  #    flaky tests and are forgiven.
  # The test results of these two kinds should both be summarized correctly.
  yield api.test(
      'summarize_both_retried_and_not_retried_test_suites',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          retry_failed_shards=True,
          additional_gtest_targets=['component_unittests', 'url_unittests'],
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
              'component_unittests': 'cccccccccccccccccccccccccccccccccccccccc',
              'url_unittests': 'dddddddddddddddddddddddddddddddddddddddd',
          },
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(base_unittests_results), retcode=1),
              failure=True)),
      api.override_step_data(
          'url_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(url_unittests_results), retcode=1),
              failure=True)),
      api.override_step_data(
          'url_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(url_unittests_retry_shards_results), retcode=1),
              failure=True)),
      api.step_data(
          'query known flaky failures on CQ',
          api.json.output({
              'flakes': [{
                  'test': {
                      'step_ui_name': 'base_unittests (with patch)',
                      'test_name': 'BaseTest.One',
                  },
                  'affected_gerrit_changes': ['123', '234'],
                  'monorail_issue': '999',
              }]
          })),
      api.post_process(
          post_process.StepTextContains,
          'base_unittests (test results summary)', [
              'Tests failed with patch, but ignored as they are known to be '
              'flaky:<br/>BaseTest.One: crbug.com/999<br/>'
          ]),
      api.post_process(post_process.StepTextContains,
                       'url_unittests (test results summary)', [
                           'Tests failed with patch, and caused build to fail:'
                           '<br/>UrlTest.One<br/>'
                       ]),
      api.post_process(post_process.DropExpectation),
  )

  results_with_success = {
      'per_iteration_data': [{
          'BaseTest.One': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'SUCCESS',
          },],
      }]
  }
  results_with_failure = {
      'per_iteration_data': [{
          'BaseTest.One': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'FAILURE',
          },],
      }]
  }
  inv_bundle_successful = {
      'id1':
          api.resultdb.Invocation(
              proto=invocation_pb2.Invocation(
                  state=invocation_pb2.Invocation.FINALIZED),
              test_results=[
                  test_result_pb2.TestResult(
                      test_id='name of no importance 1',
                      expected=True,
                      status=test_result_pb2.PASS,
                  ),
              ],
          ),
      'id2':
          api.resultdb.Invocation(
              proto=invocation_pb2.Invocation(
                  state=invocation_pb2.Invocation.FINALIZED),
              test_results=[
                  test_result_pb2.TestResult(
                      test_id='name of no importance 2',
                      expected=True,
                      status=test_result_pb2.FAIL,
                  ),
              ],
          ),
      'id3':
          api.resultdb.Invocation(
              proto=invocation_pb2.Invocation(
                  state=invocation_pb2.Invocation.FINALIZED),
              test_results=[
                  test_result_pb2.TestResult(
                      test_id='name of no importance 3.a',
                      expected=True,
                      status=test_result_pb2.PASS,
                  ),
                  test_result_pb2.TestResult(
                      test_id='name of no importance 3.b',
                      expected=True,
                      status=test_result_pb2.PASS,
                  ),
              ],
          ),
  }
  inv_bundle_broken = {
      'id1':
          api.resultdb.Invocation(
              proto=invocation_pb2.Invocation(
                  state=invocation_pb2.Invocation.FINALIZED),
              test_results=[
                  test_result_pb2.TestResult(
                      test_id='name of no importance 1',
                      expected=False,
                      status=test_result_pb2.FAIL,
                  ),
              ],
          ),
      'id2':
          api.resultdb.Invocation(
              proto=invocation_pb2.Invocation(
                  state=invocation_pb2.Invocation.FINALIZED),
              test_results=[
                  test_result_pb2.TestResult(
                      test_id='name of no importance 2',
                      expected=False,
                      status=test_result_pb2.FAIL,
                  ),
              ],
          ),
      'id3':
          api.resultdb.Invocation(
              proto=invocation_pb2.Invocation(
                  state=invocation_pb2.Invocation.FINALIZED),
              test_results=[
                  test_result_pb2.TestResult(
                      test_id='name of no importance 3.a',
                      expected=True,
                      status=test_result_pb2.PASS,
                  ),
                  test_result_pb2.TestResult(
                      test_id='name of no importance 3.b',
                      expected=False,
                      status=test_result_pb2.FAIL,
                  ),
              ],
          ),
  }
  yield api.test(
      'warn_for_retry_if_there_are_too_many_unexpected_results',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          retry_failed_shards=True,
          additional_gtest_targets=['target1', 'target2', 'target3'],
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
              'target1': '1111111111111111111111111111111111111111',
              'target2': '2222222222222222222222222222222222222222',
              'target3': '3333333333333333333333333333333333333333',
          },
          **{
              '$build/test_utils': {
                  'min_failed_suites_to_skip_retry': 3,
              },
          }),
      api.resultdb.query(
          inv_bundle_broken, step_name='query test results (with patch)'),
      api.override_step_data(
          'target1 (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(results_with_success), retcode=0),
              failure=False)),
      api.override_step_data(
          'target2 (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(results_with_success), retcode=0),
              failure=False)),
      api.override_step_data(
          'target3 (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(results_with_success), retcode=0),
              failure=False)),
      api.post_process(post_process.MustRunRE,
                       'skip retrying .* a problem with the CL'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'skip_retrying_if_there_are_too_many_failed_test_suites',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          retry_failed_shards=True,
          additional_gtest_targets=['target1', 'target2', 'target3'],
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
              'target1': '1111111111111111111111111111111111111111',
              'target2': '2222222222222222222222222222222222222222',
              'target3': '3333333333333333333333333333333333333333',
          },
          **{
              '$build/test_utils': {
                  'min_failed_suites_to_skip_retry': 3,
              },
          }),
      api.override_step_data(
          'target1 (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(results_with_failure), retcode=1),
              failure=True)),
      api.override_step_data(
          'target2 (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(results_with_failure), retcode=1),
              failure=True)),
      api.override_step_data(
          'target3 (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(results_with_failure), retcode=1),
              failure=True)),
      api.post_process(
          post_process.MustRun,
          'skip retrying because there are >= 3 test suites with test failures '
          'and it most likely indicates a problem with the CL'),
      api.post_process(post_process.DoesNotRunRE,
                       'target\d \(retry shards with patch\)'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'warn_but_not_retry_if_failures_but_no_unexpected_results',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          retry_failed_shards=True,
          additional_gtest_targets=['target1', 'target2', 'target3'],
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
              'target1': '1111111111111111111111111111111111111111',
              'target2': '2222222222222222222222222222222222222222',
              'target3': '3333333333333333333333333333333333333333',
          },
          **{
              '$build/test_utils': {
                  'min_failed_suites_to_skip_retry': 3,
              },
          }),
      api.resultdb.query(
          inv_bundle_successful, step_name='query test results (with patch)'),
      api.override_step_data(
          'target1 (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(results_with_failure), retcode=1),
              failure=True)),
      api.override_step_data(
          'target2 (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(results_with_failure), retcode=1),
              failure=True)),
      api.override_step_data(
          'target3 (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(results_with_failure), retcode=1),
              failure=True)),
      api.post_process(post_process.MustRunRE,
                       'skip retrying .* a problem with the CL'),
      api.post_process(post_process.MustRun, 'Migration mismatch'),
      api.post_process(post_process.DoesNotRunRE,
                       'target\d \(retry shards with patch\)'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_and_warn_if_unexpected_results_but_no_failures',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          retry_failed_shards=True,
          additional_gtest_targets=['target1', 'target2', 'target3'],
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
              'target1': '1111111111111111111111111111111111111111',
              'target2': '2222222222222222222222222222222222222222',
              'target3': '3333333333333333333333333333333333333333',
          },
          **{
              '$build/test_utils': {
                  'min_failed_suites_to_skip_retry': 3,
              },
          }),
      api.resultdb.query(
          inv_bundle_broken, step_name='query test results (with patch)'),
      api.override_step_data(
          'target1 (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(results_with_success), retcode=0),
              failure=False)),
      api.override_step_data(
          'target2 (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(results_with_failure), retcode=1),
              failure=False)),
      api.override_step_data(
          'target3 (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(results_with_failure), retcode=1),
              failure=False)),
      api.post_process(post_process.MustRunRE,
                       'skip retrying .* a problem with the CL'),
      api.post_process(post_process.MustRun, 'Migration mismatch'),
      api.post_process(post_process.DropExpectation),
  )
