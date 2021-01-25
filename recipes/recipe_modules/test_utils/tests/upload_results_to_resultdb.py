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
    test_spec = steps.SwarmingGTestTestSpec.create('base_unittests', shards=2)
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
          step_name='query test results (with patch)',
      ),
      api.post_process(post_process.MustRun, 'query test results (with patch)'),
      api.post_process(post_process.StepSuccess,
                       'query test results (with patch)'),
      api.post_process(post_process.MustRun,
                       'include derived test results (with patch)'),
      api.post_process(post_process.StepSuccess,
                       'include derived test results (with patch)'),
      api.post_process(post_process.DoesNotRun,
                       'include derived test results (without patch)'),
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
      api.override_step_data('query test results (with patch)'),
      api.override_step_data('query test results (retry shards with patch)'),
      api.post_process(post_process.MustRun, 'query test results (with patch)'),
      api.post_process(post_process.StepSuccess,
                       'query test results (with patch)'),
      api.post_process(post_process.MustRun,
                       'query test results (retry shards with patch)'),
      api.post_process(post_process.MustRun,
                       'query test results (without patch)'),
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
      api.post_process(post_process.DoesNotRun,
                       'query test results (with patch)'),
      api.post_process(post_process.MustRun,
                       '[skipped] query test results (with patch)'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'non_chromium_builder',
      api.builder_group.for_current('g'),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          is_swarming_test=True,
      ),
      api.buildbucket.try_build('project', 'try', 'linux-rel'),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True),
              shards=2,
              failure=False)),
      api.post_process(post_process.DoesNotRun,
                       'query test results (with patch)'),
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
          step_name='query test results (with patch)',
      ),
      api.resultdb.query(
          inv_bundle_with_failures,
          step_name='query test results (retry shards with patch)',
      ),
      api.resultdb.query(
          inv_bundle_with_failures,
          step_name='query test results (without patch)',
      ),
      api.post_process(post_process.MustRun,
                       'exonerate unexpected without patch results'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'resultdb_unenabled',
      api.builder_group.for_current('g'),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          is_swarming_test=True,
      ),
      api.buildbucket.build(
          build_pb2.Build(
              builder=builder_pb2.BuilderID(
                  project='chromium',
                  bucket='try',
                  builder='linux-rel',
              ))),
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
          step_name='query test results (with patch)',
      ),
      api.resultdb.query(
          inv_bundle_with_failures,
          step_name='query test results (retry shards with patch)',
      ),
      api.resultdb.query(
          inv_bundle_with_failures,
          step_name='query test results (without patch)',
      ),
      api.post_process(post_process.DoesNotRun,
                       'include derived test results (with patch)'),
      api.post_process(post_process.DoesNotRun,
                       'exonerate unexpected without patch results'),
      api.post_process(post_process.DropExpectation),
  )

  inv_bundle_with_unexpected_passes = {
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
                      status=test_result_pb2.PASS,
                      variant={'def': {
                          'key1': 'value1',
                      }}),
                  test_result_pb2.TestResult(
                      test_id='ninja://chromium/tests:browser_tests/t3',
                      expected=False,
                      status=test_result_pb2.FAIL,
                      variant={'def': {
                          'key1': 'value1',
                      }}),
              ],
          ),
  }

  yield api.test(
      'exonerate_unexpected_passes',
      api.chromium.ci_build(builder_group='g', builder='linux-rel'),
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
          inv_bundle_with_unexpected_passes,
          step_name='query test results (with patch)',
      ),
      api.post_process(post_process.MustRun,
                       'exonerate unexpected passes (with patch)'),
      api.post_process(post_process.DropExpectation),
  )
