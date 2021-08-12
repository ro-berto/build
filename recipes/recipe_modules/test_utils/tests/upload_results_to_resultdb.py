# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'builder_group',
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/resultdb',
    'test_utils',
]

from recipe_engine.recipe_api import Property
from recipe_engine import post_process

from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import builder as builder_pb2
from PB.go.chromium.org.luci.resultdb.proto.v1 import (invocation as
                                                       invocation_pb2)
from PB.go.chromium.org.luci.resultdb.proto.v1 import (test_result as
                                                       test_result_pb2)

from RECIPE_MODULES.build.chromium_tests import steps

PROPERTIES = {
    # This property is a boolean that indicates whether the test being run
    # is a SwarmingTest or not.
    'is_swarming_test': Property(default=True),
}


def RunSteps(api, is_swarming_test=True):
  test_spec = steps.LocalIsolatedScriptTestSpec.create('base_unittests')
  if is_swarming_test:
    test_spec = steps.SwarmingGTestTestSpec.create(
        'base_unittests',
        shards=2,
        test_id_prefix='ninja://chromium/tests:base_unittests/')
  tests = [test_spec.get_test()]
  api.chromium_swarming.path_to_merge_scripts = (
      api.path['cache'].join('merge_scripts'))
  api.chromium_swarming.set_default_dimension('pool', 'foo')

  api.test_utils.run_tests(
      api.chromium_tests.m,
      tests,
      'with patch',
      retry_failed_shards=True,
      retry_invalid_shards=True)

  api.test_utils.run_tests(api.chromium_tests.m, tests, 'without patch')


def GenTests(api):
  inv_bundle = {
      'invid':
          api.resultdb.Invocation(
              proto=invocation_pb2.Invocation(
                  state=invocation_pb2.Invocation.FINALIZED),),
      'invid2':
          api.resultdb.Invocation(
              proto=invocation_pb2.Invocation(
                  state=invocation_pb2.Invocation.FINALIZED),),
  }

  yield api.test(
      'include_invocation',
      api.chromium.try_build(builder_group='g', builder='linux-rel'),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          is_swarming_test=True,
      ),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False),
              shards=2,
              failure=False)),
      api.resultdb.query(
          inv_bundle,
          step_name='query test results (with patch).base_unittests',
      ),
      api.post_process(post_process.MustRun,
                       'query test results (with patch).base_unittests'),
      api.post_process(post_process.StepSuccess,
                       'query test results (with patch).base_unittests'),
      api.post_process(post_process.MustRun,
                       'include task invocations (with patch)'),
      api.post_process(post_process.StepSuccess,
                       'include task invocations (with patch)'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'swarming_test_results',
      api.chromium.try_build(builder_group='g', builder='linux-rel'),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          is_swarming_test=True,
      ),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False),
              shards=2,
              failure=True)),
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True),
              shards=2,
              failure=False)),
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True),
              shards=2,
              failure=False)),
      api.override_step_data('query test results (with patch).base_unittests'),
      api.override_step_data(
          'query test results (retry shards with patch).base_unittests'),
      api.post_process(post_process.MustRun,
                       'query test results (with patch).base_unittests'),
      api.post_process(post_process.StepSuccess,
                       'query test results (with patch).base_unittests'),
      api.post_process(
          post_process.MustRun,
          'query test results (retry shards with patch).base_unittests'),
      api.post_process(post_process.MustRun,
                       'query test results (without patch).base_unittests'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'local_test_results',
      api.chromium.try_build(builder_group='g', builder='linux-rel'),
      api.properties(
          is_swarming_test=False,
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.post_process(post_process.MustRun, 'query test results (with patch)'),
      api.post_process(post_process.DropExpectation),
  )

  inv_bundle_with_failures = {
      'invid':
          api.resultdb.Invocation(
              proto=invocation_pb2.Invocation(
                  state=invocation_pb2.Invocation.FINALIZED),
              test_results=[
                  test_result_pb2.TestResult(
                      test_id='ninja://chromium/tests:browser_tests/t1',
                      expected=True,
                      status=test_result_pb2.PASS,
                      variant={'def': {
                          'key1': 'value1',
                      }}),
                  test_result_pb2.TestResult(
                      test_id='ninja://chromium/tests:browser_tests/t2',
                      expected=False,
                      status=test_result_pb2.FAIL,
                      variant={'def': {
                          'key2': 'value2',
                      }}),
                  test_result_pb2.TestResult(
                      test_id='ninja://chromium/tests:browser_tests/t2',
                      expected=False,
                      status=test_result_pb2.FAIL,
                      variant={'def': {
                          'key2': 'value2',
                      }}),
                  test_result_pb2.TestResult(
                      test_id='ninja://chromium/tests:browser_tests/t3',
                      expected=False,
                      status=test_result_pb2.PASS,
                      variant={'def': {
                          'key1': 'value1',
                      }}),
              ],
          ),
  }

  yield api.test(
      'exonerate_without_patch_failures',
      api.chromium.try_build(builder_group='g', builder='linux-rel'),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          is_swarming_test=True,
      ),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False),
              shards=2,
              failure=True)),
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True),
              shards=2,
              failure=True)),
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True),
              shards=2,
              failure=True)),
      api.resultdb.query(
          inv_bundle_with_failures,
          step_name='query test results (with patch).base_unittests',
      ),
      api.resultdb.query(
          inv_bundle_with_failures,
          step_name=('query test results (retry shards with patch).'
                     'base_unittests'),
      ),
      api.resultdb.query(
          inv_bundle_with_failures,
          step_name='query test results (without patch).base_unittests',
      ),
      api.post_process(post_process.MustRun,
                       'exonerate unexpected without patch results'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'resultdb_disabled',
      api.builder_group.for_current('g'),
      api.post_process(post_process.MustRun, 'resultdb not enabled'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  inv_bundle_with_one_failure = {
      'invid':
          api.resultdb.Invocation(
              proto=invocation_pb2.Invocation(
                  state=invocation_pb2.Invocation.FINALIZED),
              test_results=[
                  test_result_pb2.TestResult(
                      test_id='ninja://chromium/tests:base_unittests/Test.Two',
                      expected=False,
                      status=test_result_pb2.FAIL)
              ],
          ),
  }
  findit_exoneration_output = {
      'flakes': [{
          'test': {
              'step_ui_name': 'base_unittests (with patch)',
              'test_name': 'Test.Two',
          },
          'affected_gerrit_changes': ['123', '234'],
          'monorail_issue': '999',
      }]
  }
  yield api.test(
      'query_findit_with_invocation_results',
      api.chromium.ci_build(builder_group='g', builder='linux-rel'),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          is_swarming_test=True,
      ),
      api.resultdb.query(
          inv_bundle_with_one_failure,
          step_name='query test results (with patch).base_unittests',
      ),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False),
              shards=2,
              failure=False)),
      # The first query is used in the legacy decisions. The second is used in
      # RDB-based decisions. If both report the same failing test as flaky, then
      # the decision logic should match.
      api.override_step_data('query known flaky failures on CQ',
                             api.json.output(findit_exoneration_output)),
      api.override_step_data('query known flaky failures on CQ (2)',
                             api.json.output(findit_exoneration_output)),
      api.post_process(post_process.DoesNotRun,
                       'Migration mismatch (informational)'),
      api.post_process(post_process.DropExpectation),
  )

  inv_bundle_with_different_test_name = {
      'invid':
          api.resultdb.Invocation(
              proto=invocation_pb2.Invocation(
                  state=invocation_pb2.Invocation.FINALIZED),
              test_results=[
                  test_result_pb2.TestResult(
                      test_id='ninja://chromium/tests:base_unittests/Test.Two',
                      expected=False,
                      status=test_result_pb2.FAIL,
                      tags=[{
                          'key': 'test_name',
                          'value': 'Different.Test.Name'
                      }]),
              ],
          ),
  }
  yield api.test(
      'results_from_rdb_with_different_test_names',
      api.chromium.ci_build(builder_group='g', builder='linux-rel'),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          is_swarming_test=True,
      ),
      api.resultdb.query(
          inv_bundle_with_different_test_name,
          step_name='query test results (with patch).base_unittests',
      ),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False),
              shards=2,
              failure=False)),
      # We give the failing test a different name when reported by RDB. So make
      # sure the old test name is sent to FindIt in the legacy decision-making
      # flow and the overridden name is sent to FindIt in the new flow.
      api.post_process(post_process.LogContains,
                       'query known flaky failures on CQ', 'input',
                       ['Test.Two']),
      api.post_process(post_process.LogContains,
                       'query known flaky failures on CQ (2)', 'input',
                       ['Different.Test.Name']),
      api.post_process(post_process.DropExpectation),
  )
