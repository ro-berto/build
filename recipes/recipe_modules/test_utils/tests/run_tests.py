# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'builder_group',
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'depot_tools/tryserver',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/resultdb',
    'recipe_engine/step',
    'skylab',
    'test_results',
    'test_utils',
]

from recipe_engine.recipe_api import Property
from recipe_engine import post_process

from RECIPE_MODULES.build import skylab
from RECIPE_MODULES.build.chromium_tests import steps

from PB.go.chromium.org.luci.resultdb.proto.v1 import (invocation as
                                                       rdb_invocation)
from PB.go.chromium.org.luci.resultdb.proto.v1 import (test_result as
                                                       rdb_test_result)
from PB.go.chromium.org.luci.resultdb.proto.v1 import common as rdb_common

PROPERTIES = {
    'abort_on_failure': Property(default=False),
    'test_swarming': Property(default=False),
    'test_skylab': Property(default=False),
    'test_name': Property(default='MockTest'),
    'retry_failed_shards': Property(default=False),
    'retry_invalid_shards': Property(default=False),
}


def RunSteps(api, test_swarming, test_skylab, test_name, abort_on_failure,
             retry_failed_shards, retry_invalid_shards):
  api.chromium.set_config('chromium')
  api.chromium_tests.set_config('chromium')
  api.test_results.set_config('public_server')
  api.chromium_swarming.path_to_merge_scripts = (
      api.path['cache'].join('merge_scripts'))
  api.chromium_swarming.set_default_dimension('pool', 'foo')

  class MockSwarmingTestSpec(steps.SwarmingIsolatedScriptTestSpec):

    @property
    def test_class(self):
      return MockSwarmingTest

  class MockSwarmingTest(steps.SwarmingIsolatedScriptTest):

    def deterministic_failures(self, suffix):
      if self.name.endswith('failed_results') or self.name.endswith(
          'invalid_results'):
        return [self]
      return super(MockSwarmingTest, self).deterministic_failures(suffix)

    def has_valid_results(self, suffix):
      if self.name.endswith('invalid_results'):
        return False
      return super(MockSwarmingTest, self).has_valid_results(suffix)

  if test_swarming:
    test_specs = [
        MockSwarmingTestSpec.create(name=test_name),
        MockSwarmingTestSpec.create(name=test_name + '_2'),
        steps.MockTestSpec.create(name='test3')
    ]
    api.chromium_tests.set_config('staging')
  elif test_skylab:
    test_specs = []
    for spec in api.properties['src_spec']:
      common_skylab_kwargs = {
          k: v
          for k, v in spec.items()
          if k in ['cros_board', 'cros_img', 'tast_expr']
      }
      test_specs.append(
          steps.SkylabTestSpec.create(spec.get('name'), **common_skylab_kwargs))
  else:
    test_specs = [
        steps.MockTestSpec.create(
            name=test_name, abort_on_failure=abort_on_failure),
        steps.MockTestSpec.create(name='test2')
    ]

  tests = [s.get_test() for s in test_specs]

  _, failed_tests = api.test_utils.run_tests(
      api.chromium_tests.m,
      tests,
      '',
      retry_failed_shards=retry_failed_shards,
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
      api.chromium.generic_build(
          builder_group='test_group', builder='test_builder'),
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
          ([['0'], ['1']], 1),
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
          ([['1']], 1),
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
          ([['0'], ['1']], 1),
      ]),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'success_skylab_test',
      api.chromium.generic_build(
          builder_group='test_group', builder='test_builder'),
      api.properties(
          src_spec=[{
              "cros_board": "eve",
              "cros_img": "eve-release/R89-13631.0.0",
              "name": "basic_EVE_TOT",
              "tast_expr": "lacros.Basic",
              "swarming": {},
              "test": "basic",
              "timeout": 3600
          }],
          test_skylab=True,
      ),
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
          ([['0'], ['1']], 1),
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

  yield api.test(
      'failure_swarming',
      api.chromium.ci_build(builder='test_builder'),
      api.properties(
          test_name='base_unittests_failed_results',
          test_swarming=True,
          swarm_hashes={
              'base_unittests_failed_results':
                  '[dummy hash for base_unittests]',
              'base_unittests_failed_results_2':
                  '[dummy hash for base_unittests_2]',
          },
          retry_failed_shards=True,
          retry_invalid_shards=True,
      ),
      api.post_process(post_process.MustRun, 'test3'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failure_with_resultsdb',
      api.chromium.ci_build(builder='test_builder'),
      api.properties(
          test_name='base_unittests_failed_results',
          test_swarming=True,
          swarm_hashes={
              'base_unittests_failed_results':
                  '[dummy hash for base_unittests]',
              'base_unittests_failed_results_2':
                  '[dummy hash for base_unittests_2]',
          },
          retry_failed_shards=True,
          retry_invalid_shards=True,
      ),
      api.override_step_data(
          'query test results',
          stdout=api.json.invalid(
              api.resultdb.serialize({
                  "invid":
                      api.resultdb.Invocation(
                          proto=rdb_invocation.Invocation(
                              state=rdb_invocation.Invocation.FINALIZED,
                              name='base_unittests_failed_results'),
                          test_results=(rdb_test_result.TestResult(
                              test_id='base_unittests_failed_results',
                              variant=rdb_common.Variant(
                                  **{
                                      'def': {
                                          'test_suite':
                                              'base_unittests_failed_results'
                                      }
                                  }),
                              expected=False,
                              status=rdb_test_result.FAIL),),
                      )
              })),
      ),
      api.post_process(post_process.MustRun, 'test3'),
      api.post_process(post_process.StatusFailure),
  )
