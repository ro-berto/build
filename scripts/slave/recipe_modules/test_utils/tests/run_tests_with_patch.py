# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'recipe_engine/properties',
    'recipe_engine/step',

    'chromium_swarming',
    'chromium_tests',
    'test_utils',
]

from recipe_engine.recipe_api import Property
from recipe_engine import post_process

PROPERTIES = {
  'has_valid_results': Property(default=True),
}

def RunSteps(api, has_valid_results):
  tests = [
      api.chromium_tests.steps.MockTest(
          name='test', has_valid_results=has_valid_results),
      api.chromium_tests.steps.MockTest(name='test2'),
  ]
  invalid, failing = api.test_utils.run_tests_with_patch(api, tests)
  if invalid:
    api.step('%s invalid' % (','.join(sorted(t.name for t in invalid))), None)
  else:
    api.step('NONE invalid', None)
  if failing:
    api.step('%s failing' % (','.join(sorted(t.name for t in failing))), None)
  else:
    api.step('NONE failing', None)


def GenTests(api):
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
