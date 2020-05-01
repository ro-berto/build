# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_swarming',
    'chromium_tests',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/resultdb',
    'test_utils',
]

from recipe_engine.recipe_api import Property
from recipe_engine import post_process

from PB.go.chromium.org.luci.resultdb.proto.rpc.v1 import (invocation as
                                                           invocation_pb2)

from RECIPE_MODULES.build.chromium_tests import steps

PROPERTIES = {
    # This property is a boolean that indicates whether the test being run
    # is a SwarmingTest or not.
    'is_swarming_test': Property(default=True),
}


def RunSteps(api, is_swarming_test=True):
  tests = [steps.LocalIsolatedScriptTest('base_unittests')]
  if is_swarming_test:
    tests = [
        steps.SwarmingGTestTest('base_unittests', shards=2),
    ]

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
      api.properties(
          mastername='m',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          is_swarming_test=True,
      ), api.buildbucket.try_build('chromium', 'try', 'linux-rel'),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False),
              shards=2,
              failure=False)),
      api.resultdb.chromium_derive(
          step_name='derive test results (with patch)',
          results=inv_bundle,
      ),
      api.post_process(post_process.MustRun,
                       'derive test results (with patch)'),
      api.post_process(post_process.StepSuccess,
                       'derive test results (with patch)'),
      api.post_process(post_process.MustRun,
                       'include derived test results (with patch)'),
      api.post_process(post_process.StepCommandContains,
                       'include derived test results (with patch)',
                       ['invid,invid2']),
      api.post_process(post_process.DoesNotRun,
                       'include derived test results (without patch)'),
      api.post_process(post_process.DropExpectation))

  yield api.test(
      'swarming_test_results',
      api.properties(
          mastername='m',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          is_swarming_test=True,
      ), api.buildbucket.try_build('chromium', 'try', 'linux-rel'),
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
      api.override_step_data('derive test results (with patch)'),
      api.override_step_data('derive test results (retry shards with patch)'),
      api.post_process(post_process.MustRun,
                       'derive test results (with patch)'),
      api.post_process(post_process.StepSuccess,
                       'derive test results (with patch)'),
      api.post_process(post_process.MustRun,
                       'derive test results (retry shards with patch)'),
      api.post_process(post_process.MustRun,
                       'derive test results (without patch)'),
      api.post_process(post_process.DropExpectation))

  yield api.test(
      'local_test_results',
      api.properties(
          mastername='m',
          is_swarming_test=False,
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }), api.buildbucket.try_build('chromium', 'try', 'linux-rel'),
      api.post_process(post_process.DoesNotRun,
                       'derive test results (with patch)'),
      api.post_process(post_process.MustRun,
                       '[skipped] derive test results (with patch)'),
      api.post_process(post_process.DropExpectation))

  yield api.test(
      'non_chromium_builder',
      api.properties(
          mastername='m',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          is_swarming_test=True,
      ), api.buildbucket.try_build('project', 'try', 'linux-rel'),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True),
              shards=2,
              failure=False)),
      api.post_process(post_process.DoesNotRun,
                       'derive test results (with patch)'),
      api.post_process(post_process.DropExpectation))
