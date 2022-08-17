# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'recipe_engine/properties',
    'recipe_engine/step',
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'flakiness',
    'test_utils',
]

from recipe_engine.recipe_api import Property
from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import steps

PROPERTIES = {
    'retry_failed_shards': Property(default=False),

    # This properties is a list of objects that will be applied when creating
    # |MockTest| for testing. If the number of test_kwargs is less than the number
    # of |MockTest|, then only the first length(test_kwargs_list) tests will have
    # matching test_kwargs to apply.
    #
    # test_kwargs is used to control the behavior of the tests run, such as
    # whether it runs on swarming (runs_on_swarming), whether the test results is
    # valid (has_valid_results and per_suffix valid) and what are the test
    # failures (per_suffix_failures).
    'test_kwargs_list': Property(default=[]),
}


def RunSteps(api, retry_failed_shards, test_kwargs_list):

  def _get_test_kwargs_by_index(index):
    if index < len(test_kwargs_list):
      return test_kwargs_list[index]

    return {}

  run_tests_kwargs = {}
  if retry_failed_shards:
    run_tests_kwargs['retry_failed_shards'] = retry_failed_shards

  test_specs = [
      steps.MockTestSpec.create(
          name='test', invertable=True, **_get_test_kwargs_by_index(0)),
      steps.MockTestSpec.create(
          name='test2', invertable=True, **_get_test_kwargs_by_index(1)),
      steps.MockTestSpec.create(
          name='test3', invertable=False, **_get_test_kwargs_by_index(2)),
  ]

  tests = [s.get_test(api.chromium_tests) for s in test_specs]

  invalid, failing = api.test_utils.run_inverted_tests_with_patch(
      tests, **run_tests_kwargs)

  if invalid:
    api.step('%s invalid' % ','.join(sorted(t.name for t in invalid)), None)
  else:
    api.step('NONE invalid', None)

  if failing:
    failed_tests_s = ','.join(t.name for t in failing)

    api.step('%s failing' % failed_tests_s, None)
  else:
    api.step('NONE failing', None)


def GenTests(api):
  yield api.test(
      'success',
      api.chromium.try_build(builder_group='g', builder='linux-rel'),
      api.post_process(post_process.MustRun, 'test (inverted with patch)'),
      api.post_process(post_process.MustRun, 'test2 (inverted with patch)'),
      api.post_process(post_process.DoesNotRun, 'test3 (inverted with patch)'),
      api.post_process(post_process.MustRun, 'NONE invalid'),
      api.post_process(post_process.MustRun, 'NONE failing'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'invalid_results',
      api.chromium.try_build(builder_group='g', builder='linux-rel'),
      api.properties(test_kwargs_list=[
          {
              'has_valid_results': False
          },
      ]),
      api.post_process(post_process.MustRun, 'test (inverted with patch)'),
      api.post_process(post_process.MustRun, 'test2 (inverted with patch)'),
      api.post_process(post_process.DoesNotRun, 'test3 (inverted with patch)'),
      api.post_process(post_process.MustRun, 'test invalid'),
      api.post_process(post_process.MustRun, 'test failing'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_shards_retry_succeeds',
      api.chromium.try_build(builder_group='g', builder='linux-rel'),
      api.properties(
          retry_failed_shards=True,
          test_kwargs_list=[{
              'runs_on_swarming': True,
              'per_suffix_failures': {
                  'inverted with patch': ['testA']
              },
          }]),
      api.post_process(post_process.MustRun, 'test (inverted with patch)'),
      api.post_process(post_process.MustRun, 'test2 (inverted with patch)'),
      api.post_process(post_process.DoesNotRun, 'test3 (inverted with patch)'),
      api.post_process(post_process.MustRun,
                       'test (retry shards inverted with patch)'),
      api.post_process(post_process.MustRun, 'NONE invalid'),
      api.post_process(post_process.MustRun, 'NONE failing'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_shards_invalid_then_valid',
      api.chromium.try_build(builder_group='g', builder='linux-rel'),
      api.properties(
          retry_failed_shards=True,
          test_kwargs_list=[{
              'runs_on_swarming': True,
              'per_suffix_failures': {
                  'inverted with patch': ['testA', 'testB'],
              },
              'per_suffix_valid': {
                  'inverted with patch': False,
                  'retry shards inverted with patch': True,
              }
          }]),
      api.post_process(post_process.MustRun, 'test (inverted with patch)'),
      api.post_process(post_process.MustRun, 'test2 (inverted with patch)'),
      api.post_process(post_process.DoesNotRun, 'test3 (inverted with patch)'),
      api.post_process(post_process.MustRun, 'NONE invalid'),
      api.post_process(post_process.MustRun, 'NONE failing'),
      api.post_process(post_process.DropExpectation),
  )

  # This test tests that if a non-swarming test suite has invalid test results,
  # it will still be correctly classified as invalid after retrying failed
  # shards.
  yield api.test(
      'non_swarming_invalid_results',
      api.chromium.try_build(builder_group='g', builder='linux-rel'),
      api.properties(
          retry_failed_shards=True,
          test_kwargs_list=[{
              'runs_on_swarming': True,
          }, {
              'per_suffix_valid': {
                  'inverted with patch': False,
              }
          }]),
      api.post_process(post_process.MustRun, 'test (inverted with patch)'),
      api.post_process(post_process.DoesNotRun,
                       'test2 (retry shards inverted with patch)'),
      api.post_process(post_process.MustRun, 'test2 invalid'),
      api.post_process(post_process.MustRun, 'test2 failing'),
      api.post_process(post_process.DoesNotRun, 'test3 (inverted with patch)'),
      api.post_process(post_process.DropExpectation),
  )
