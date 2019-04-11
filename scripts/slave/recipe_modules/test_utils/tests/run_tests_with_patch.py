# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',

    'chromium_swarming',
    'chromium_tests',
    'test_utils',
]

from recipe_engine.recipe_api import Property
from recipe_engine import post_process

PROPERTIES = {
  'has_valid_results': Property(default=True),
  'retry_failed_shards': Property(default=None),
  'per_suffix_failures': Property(default=None),
  'per_suffix_valid': Property(default=None),
}

def RunSteps(api, has_valid_results, retry_failed_shards, per_suffix_failures,
             per_suffix_valid):
  test_kwargs = {
      'has_valid_results': has_valid_results,
  }
  run_tests_kwargs = {}

  if retry_failed_shards:
    run_tests_kwargs['retry_failed_shards'] = retry_failed_shards
    test_kwargs['runs_on_swarming'] = True
    test_kwargs['per_suffix_failures'] = per_suffix_failures
    test_kwargs['per_suffix_valid'] = per_suffix_valid

  tests = [
      api.chromium_tests.steps.MockTest(name='test', api=api, **test_kwargs),
      api.chromium_tests.steps.MockTest(name='test2', api=api),
  ]

  invalid, failing = api.test_utils.run_tests_with_patch(
      api, tests, **run_tests_kwargs)
  if invalid:
    api.step('%s invalid' % ','.join(sorted(t.name for t in invalid)), None)
  else:
    api.step('NONE invalid', None)

  if failing:
    failed_tests = []
    for t in failing:
      _, failed = t.with_patch_failures_including_retry(api)
      tup = (t.name,)
      if failed:
        tup = tup + ('#'.join(sorted(failed)),)
      failed_tests.append(':'.join(tup))

    failed_tests_s = ','.join(failed_tests)

    api.step('%s failing' % failed_tests_s, None)
  else:
    api.step('NONE failing', None)


def GenTests(api):
  # TODO(martiniss): Rewrite these tests to use assertions in RunSteps.
  yield (
      api.test('success') +
      api.post_process(post_process.MustRun, 'test (with patch)') +
      api.post_process(post_process.MustRun, 'test2 (with patch)') +
      api.post_process(post_process.MustRun, 'NONE invalid') +
      api.post_process(post_process.MustRun, 'NONE failing') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('invalid_results') +
      api.properties(has_valid_results=False) +
      api.post_process(post_process.MustRun, 'test (with patch)') +
      api.post_process(post_process.MustRun, 'test2 (with patch)') +
      api.post_process(post_process.MustRun, 'test invalid') +
      api.post_process(post_process.MustRun, 'test failing') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('retry_shards_retry_succeeds') +
      api.properties(retry_failed_shards=True, per_suffix_failures={
          'with patch': set(['testA']),
      }) +
      api.post_process(post_process.MustRun, 'test (with patch)') +
      api.post_process(post_process.MustRun, 'test2 (with patch)') +
      api.post_process(post_process.MustRun, 'NONE invalid') +
      api.post_process(post_process.MustRun, 'NONE failing') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('retry_shards_retry_still_fails') +
      api.properties(retry_failed_shards=True, per_suffix_failures={
          'with patch': set(['testA']),
          'retry shards with patch': set(['testA']),
      }) +
      api.post_process(post_process.MustRun, 'test (with patch)') +
      api.post_process(post_process.MustRun, 'test2 (with patch)') +
      api.post_process(post_process.MustRun, 'NONE invalid') +
      api.post_process(post_process.MustRun, 'test:testA failing') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('retry_shards_retry_subset_fails') +
      api.properties(retry_failed_shards=True, per_suffix_failures={
          'with patch': set(['testA', 'testB']),
          'retry shards with patch': set(['testB', 'testC']),
      }) +
      api.post_process(post_process.MustRun, 'test (with patch)') +
      api.post_process(post_process.MustRun, 'test2 (with patch)') +
      api.post_process(post_process.MustRun, 'NONE invalid') +
      api.post_process(post_process.MustRun, 'test:testB failing') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('retry_shards_invalid_then_valid') +
      api.properties(retry_failed_shards=True, per_suffix_failures={
          'with patch': set(['testA', 'testB']),
      }, per_suffix_valid={
          'with patch': False,
          'retry shards with patch': True,
      }) +
      api.post_process(post_process.MustRun, 'test (with patch)') +
      api.post_process(post_process.MustRun, 'test2 (with patch)') +
      api.post_process(post_process.MustRun, 'NONE invalid') +
      api.post_process(post_process.MustRun, 'NONE failing') +
      api.post_process(post_process.DropExpectation)
  )
