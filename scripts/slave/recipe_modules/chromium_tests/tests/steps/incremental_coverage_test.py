# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_android',
    'chromium_tests',
    'recipe_engine/properties',
    'recipe_engine/step',
]


def RunSteps(api):
  api.chromium_android.set_config('incremental_coverage_builder_tests')

  test = api.chromium_tests.steps.IncrementalCoverageTest()

  test.run(api, '')

  api.step('details', [])
  api.step.active_result.presentation.logs['details'] = [
      'compile_targets: %r' % test.compile_targets(),
      'failures: %r' % test.failures(''),
      'has_valid_results: %r' % test.has_valid_results(''),
      'uses_local_devices: %r' % test.uses_local_devices,
  ]


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(
          buildbotURL='https://example/url',
          buildername='test_buildername',
          buildnumber=123)
  )
