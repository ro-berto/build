# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'builder_group',
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'depot_tools/tryserver',
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
from PB.go.chromium.org.luci.buildbucket.proto \
  import builder_common as builder_common_pb2
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
  # TODO(crbug.com/1255217): Can remove this set_config() after android tears
  # out result_details support.
  api.chromium.set_config(
      'chromium',
      TARGET_PLATFORM=api.properties.get('target_platform', 'linux'))

  api.chromium.set_build_properties({
      'got_webrtc_revision': 'webrtc_sha',
      'got_v8_revision': 'v8_sha',
      'got_revision': 'd3adv3ggie',
      'got_revision_cp': 'refs/heads/main@{#54321}',
  })

  test_specs = []
  if not is_swarming_test:
    test_specs.append(
        steps.LocalIsolatedScriptTestSpec.create('base_unittests'))
  else:
    test_specs.append(
        steps.SwarmingGTestTestSpec.create(
            'base_unittests',
            shards=2,
            test_id_prefix='ninja://chromium/tests:base_unittests/'))
  tests = [test_spec.get_test(api.chromium_tests) for test_spec in test_specs]
  api.chromium_swarming.path_to_merge_scripts = (
      api.path['cache'].join('merge_scripts'))
  api.chromium_swarming.set_default_dimension('pool', 'foo')

  api.test_utils.run_tests(
      tests,
      'with patch',
      retry_failed_shards=True,
      retry_invalid_shards=True)

  api.test_utils.run_tests(tests, 'without patch')


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
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff/size',
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
          step_name='collect tasks (with patch).base_unittests results',
      ),
      api.post_process(post_process.MustRun,
                       'collect tasks (with patch).base_unittests results'),
      api.post_process(post_process.StepSuccess,
                       'collect tasks (with patch).base_unittests results'),
      api.post_process(
          post_process.MustRun,
          'test_pre_run (with patch).include swarming task invocations'),
      api.post_process(
          post_process.StepSuccess,
          'test_pre_run (with patch).include swarming task invocations'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'swarming_test_results',
      api.chromium.try_build(builder_group='g', builder='linux-rel'),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff/size',
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
      api.override_step_data(
          'collect tasks (with patch).base_unittests results'),
      api.override_step_data(
          'collect tasks (retry shards with patch).base_unittests results'),
      api.post_process(post_process.MustRun,
                       'collect tasks (with patch).base_unittests results'),
      api.post_process(post_process.StepSuccess,
                       'collect tasks (with patch).base_unittests results'),
      api.post_process(
          post_process.MustRun,
          'collect tasks (retry shards with patch).base_unittests results'),
      api.post_process(post_process.MustRun,
                       'collect tasks (without patch).base_unittests results'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'local_test_results',
      api.chromium.try_build(builder_group='g', builder='linux-rel'),
      api.properties(
          is_swarming_test=False,
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff/size',
          }),
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
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff/size',
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
          step_name='collect tasks (with patch).base_unittests results',
      ),
      api.resultdb.query(
          inv_bundle_with_failures,
          step_name=(
              'collect tasks (retry shards with patch).base_unittests results'),
      ),
      api.resultdb.query(
          inv_bundle_with_failures,
          step_name='collect tasks (without patch).base_unittests results',
      ),
      api.post_process(post_process.MustRun,
                       'exonerate unrelated test failures'),
      api.post_process(post_process.DropExpectation),
  )

  inv_bundle_with_skips = {
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
                      status=test_result_pb2.SKIP,
                      variant={'def': {
                          'key2': 'value2',
                      }}),
                  test_result_pb2.TestResult(
                      test_id='ninja://chromium/tests:browser_tests/t2',
                      expected=False,
                      status=test_result_pb2.SKIP,
                      variant={'def': {
                          'key2': 'value2',
                      }}),
                  test_result_pb2.TestResult(
                      test_id='ninja://chromium/tests:browser_tests/t3',
                      expected=False,
                      status=test_result_pb2.SKIP,
                      variant={'def': {
                          'key1': 'value1',
                      }}),
              ],
          ),
  }

  yield api.test(
      'dont_exonerate_without_patch_skips',
      api.chromium.try_build(builder_group='g', builder='linux-rel'),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff/size',
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
          step_name='collect tasks (with patch).base_unittests results',
      ),
      api.resultdb.query(
          inv_bundle_with_failures,
          step_name=(
              'collect tasks (retry shards with patch).base_unittests results'),
      ),
      api.resultdb.query(
          inv_bundle_with_skips,
          step_name='collect tasks (without patch).base_unittests results',
      ),
      api.post_process(post_process.DoesNotRun,
                       'exonerate unrelated test failures'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'resultdb_disabled',
      api.builder_group.for_current('g'),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff/size',
          },
          is_swarming_test=True,
      ),
      api.buildbucket.build(
          build_pb2.Build(
              builder=builder_common_pb2.BuilderID(
                  project='chromium',
                  bucket='try',
                  builder='linux-rel',
              ))),
      api.post_process(post_process.MustRun, 'resultdb not enabled'),
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
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff/size',
          },
          is_swarming_test=True,
      ),
      api.resultdb.query(
          inv_bundle_with_different_test_name,
          step_name='collect tasks (with patch).base_unittests results',
      ),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False),
              shards=2,
              failure=False)),
      api.post_process(post_process.LogContains,
                       'query known flaky failures on CQ', 'input',
                       ['Different.Test.Name']),
      api.post_process(post_process.DropExpectation),
  )
