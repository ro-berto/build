# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/step',
    'test_utils',
]


def RunSteps(api):
  api.chromium.set_config('chromium')

  test = api.chromium_tests.steps.PrintPreviewTests()

  try:
    test.run(api, '')
  finally:
    api.step('details', [])
    api.step.active_result.presentation.logs['details'] = [
        'compile_targets: %r' % test.compile_targets(api),
        'failures: %r' % test.failures(api, ''),
        'has_valid_results: %r' % test.has_valid_results(api, ''),
        'uses_local_devices: %r' % test.uses_local_devices,
    ]


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(buildername='test_buildername', bot_id='test_bot_id')
  )
