# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_tests',
    'depot_tools/gsutil',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
    'recipe_engine/tempfile',
]


def RunSteps(api):
  api.chromium.set_config('chromium')

  test = api.chromium_tests.steps.FindAnnotatedTest()

  api.step('details', [])
  api.step.active_result.presentation.logs['details'] = [
      'compile_targets: %r' % test.compile_targets(api)
  ]

  test.run(api, '')


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(
          buildername='test_buildername',
          current_time='20170425T203027')
  )
