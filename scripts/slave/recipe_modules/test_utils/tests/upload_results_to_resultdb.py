# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_swarming',
    'chromium_tests',
    'recipe_engine/json',
    'recipe_engine/properties',
    'test_utils',
]

from recipe_engine.recipe_api import Property
from recipe_engine import post_process

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

  yield api.test(
      'swarming_test_results',
      api.properties(
          mastername='m',
          buildername='linux-rel',
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
      api.override_step_data('derive test results (with patch)'),
      api.override_step_data('derive test results (retry shards with patch)'),
      api.post_process(post_process.MustRun,
                       'derive test results (with patch)'),
      api.post_process(post_process.StepSuccess,
                       'derive test results (with patch)'),
      api.post_process(post_process.MustRun,
                       'derive test results (retry shards with patch)'),
      api.post_process(post_process.DoesNotRun,
                       'derive test results (without patch)'),
      api.post_process(post_process.DropExpectation))

  yield api.test(
      'local_test_results',
      api.properties(
          mastername='m',
          buildername='linux-rel',
          is_swarming_test=False,
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.post_process(post_process.DoesNotRun,
                       'derive test results (with patch)'),
      api.post_process(post_process.MustRun,
                       '[skipped] derive test results (with patch)'),
      api.post_process(post_process.DropExpectation))

  yield api.test(
      'non_linux-rel_builder',
      api.properties(
          mastername='m',
          buildername='mac-rel',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          is_swarming_test=True,
      ),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True),
              shards=2,
              failure=False)),
      api.post_process(post_process.DoesNotRun,
                       'derive test results (with patch)'),
      api.post_process(post_process.DropExpectation))
