# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'builder_group',
    'chromium',
    'chromium_tests',
    'depot_tools/tryserver',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/step',
    'chromium_swarming',
    'test_results',
    'test_utils',
]

from recipe_engine.recipe_api import Property
from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import steps

PROPERTIES = {
  'abort_on_failure': Property(default=False),
  'test_swarming': Property(default=False),
  'test_name': Property(default='MockTest'),
  'retry_invalid_shards': Property(default=False),
}

def RunSteps(api, test_swarming, test_name, abort_on_failure,
             retry_invalid_shards):
  api.chromium.set_config('chromium')
  api.chromium_tests.set_config('chromium')
  api.test_results.set_config('public_server')

  class MockSwarmingTest(steps.SwarmingIsolatedScriptTest, steps.MockTest):

    def __init__(self, name, api):
      super(MockSwarmingTest, self).__init__(name=name, api=api)

    def has_valid_results(self, suffix):
      if self.name.endswith('invalid_results'):
        return False
      return super(MockSwarmingTest, self).has_valid_results(suffix)

  if test_swarming:
    tests = [
        MockSwarmingTest(name=test_name, api=api),
        MockSwarmingTest(name=test_name + '_2', api=api),
        steps.MockTest(name='test3', api=api)
    ]
    api.chromium_tests.set_config('staging')
  else:
    tests = [
        steps.MockTest(
            name=test_name, abort_on_failure=abort_on_failure, api=api),
        steps.MockTest(name='test2', api=api)
    ]

  _, failed_tests = api.test_utils.run_tests(
      api.chromium_tests.m, tests, '',
      retry_invalid_shards=retry_invalid_shards)
  if failed_tests:
    raise api.step.StepFailure(
        'failed: %s' % ' '.join(t.name for t in failed_tests))


def GenTests(api):
  failure_code = steps.MockTest.ExitCodes.FAILURE
  infra_code = steps.MockTest.ExitCodes.INFRA_FAILURE

  yield api.test(
      'success',
      api.chromium.generic_build(
          builder_group='test_group', builder='test_builder'),
      api.properties(test_name='base_unittests'),
      api.post_process(post_process.MustRun, 'test2'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'success_swarming',
      api.builder_group.for_current('test_group'),
      api.properties(
          buildername='test_buildername',
          bot_id='test_bot_id',
          buildnumber=123,
          test_name='base_unittests',
          test_swarming=True,
          swarm_hashes={
              'base_unittests': '[dummy hash for base_unittests]',
              'base_unittests_2': '[dummy hash for base_unittests_2]',
          }),
      api.chromium_swarming.wait_for_finished_task_set([
          ([], 1),
          ([['10000'], ['110000']], 1),
      ]),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'success_swarming_one_task_still_pending',
      api.chromium.generic_build(
          builder_group='test_group', builder='test_builder'),
      api.properties(
          test_name='base_unittests',
          test_swarming=True,
          swarm_hashes={
              'base_unittests': '[dummy hash for base_unittests]',
              'base_unittests_2': '[dummy hash for base_unittests_2]',
          }),
      api.chromium_swarming.wait_for_finished_task_set([
          ([], 1),
          ([['110000']], 1),
      ]),
      # There's no call to get_states after there's only one test left pending,
      # as the test_utils logic just calls the regular collect logic on that
      # test.
      api.post_process(post_process.MustRun, 'base_unittests'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'success_swarming_long_pending',
      api.chromium.generic_build(
          builder_group='test_group', builder='test_builder'),
      api.properties(
          test_name='base_unittests',
          test_swarming=True,
          swarm_hashes={
              'base_unittests': '[dummy hash for base_unittests]',
              'base_unittests_2': '[dummy hash for base_unittests_2]',
          }),
      api.chromium_swarming.wait_for_finished_task_set([
          ([], 1),
          ([], 1),
          ([], 1),
          ([], 1),
          ([], 1),
          ([['10000'], ['110000']], 1),
      ]),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failure',
      api.chromium.generic_build(
          builder_group='test_group', builder='test_builder'),
      api.properties(test_name='base_unittests'),
      api.override_step_data('base_unittests', retcode=failure_code),
      api.post_process(post_process.MustRun, 'test2'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failure_abort',
      api.chromium.generic_build(
          builder_group='test_group', builder='test_builder'),
      api.properties(test_name='base_unittests', abort_on_failure=True),
      api.override_step_data('base_unittests', retcode=failure_code),
      api.post_process(post_process.DoesNotRun, 'test2'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'infra_failure',
      api.chromium.generic_build(
          builder_group='test_group', builder='test_builder'),
      api.properties(test_name='base_unittests'),
      api.override_step_data('base_unittests', retcode=infra_code),
      api.post_process(post_process.DoesNotRun, 'test2'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'retry_invalid_swarming',
      api.chromium.generic_build(
          builder_group='test_group', builder='test_builder'),
      api.properties(
          test_name='base_unittests_invalid_results',
          test_swarming=True,
          retry_invalid_shards=True,
          swarm_hashes={
              'base_unittests_invalid_results':
                  '[dummy hash for base_unittests]',
              'base_unittests_invalid_results_2':
                  '[dummy hash for base_unittests_2]',
          }),
      api.chromium_swarming.wait_for_finished_task_set([
          ([], 1),
          ([['10000'], ['110000']], 1),
      ]),
      api.post_process(post_process.MustRun,
                       'base_unittests_invalid_results (retry shards)'),
      api.post_process(post_process.DoesNotRun,
                       'base_unittests_invalid_results_2 (retry shards)'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'pre_run_failure',
      api.chromium.generic_build(
          builder_group='test_group', builder='test_builder'),
      api.properties(test_name='base_unittests'),
      api.override_step_data(
          'test_pre_run.pre_run base_unittests', retcode=failure_code),
      api.post_process(post_process.MustRun, 'base_unittests'),
      api.post_process(post_process.MustRun, 'test2'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'pre_run_infra_failure',
      api.chromium.generic_build(
          builder_group='test_group', builder='test_builder'),
      api.properties(test_name='base_unittests'),
      api.override_step_data(
          'test_pre_run.pre_run base_unittests', retcode=infra_code),
      api.post_process(post_process.DoesNotRun, 'base_unittests'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )
