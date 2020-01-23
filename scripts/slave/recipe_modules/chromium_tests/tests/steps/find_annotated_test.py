# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'depot_tools/gsutil',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
]

from RECIPE_MODULES.build.chromium_tests import steps


def RunSteps(api):
  api.chromium.set_config('chromium')

  test = steps.FindAnnotatedTest()

  api.step('details', [])
  api.step.active_result.presentation.logs['details'] = [
      'compile_targets: %r' % test.compile_targets()
  ]

  test.run(api, '')


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.ci_build(builder='test_buildername'),
      api.properties(current_time='20170425T203027'),
  )
