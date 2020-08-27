# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'recipe_engine/buildbucket',
    'recipe_engine/properties',
    'recipe_engine/step',
]

from RECIPE_MODULES.build.chromium_tests import steps


def RunSteps(api):
  api.chromium.set_config('chromium')

  test = steps.SizesStep(
      results_url='https://example/url', perf_id='test-perf-id')

  try:
    test.run(api, '')
  finally:
    api.step('details', [])
    api.step.active_result.presentation.logs['details'] = [
        'compile_targets: %r' % test.compile_targets(),
        'uses_local_devices: %r' % test.uses_local_devices,
        'has_valid_results: %r' % test.has_valid_results(''),
        'failures: %r' % test.failures(''),
    ]


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.ci_build(builder='test_buildername',),
  )
