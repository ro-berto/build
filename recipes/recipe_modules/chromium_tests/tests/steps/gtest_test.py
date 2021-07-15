# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'depot_tools/bot_update',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'test_results',
    'test_utils',
]

from RECIPE_MODULES.build.chromium_tests import steps


def RunSteps(api):
  api.chromium.set_config('chromium')
  api.test_results.set_config('public_server')

  test = steps.LocalGTestTestSpec.create('base_unittests').get_test()

  test_options = steps.TestOptions(
      repeat_count=2, test_filter=['foo.bar'], retry_limit=3, run_disabled=True)
  test.test_options = test_options

  try:
    test.run(api, '')
  finally:
    api.step('details', [])
    api.step.active_result.presentation.logs['details'] = [
        'compile_targets: %r' % test.compile_targets(),
        'step_metadata: %r' % test.step_metadata(''),
        'pass_fail_counts: %r' % test.pass_fail_counts(''),
        'uses_local_devices: %r' % test.uses_local_devices,
    ]


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
  )
