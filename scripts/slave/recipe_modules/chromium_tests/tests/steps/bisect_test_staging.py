# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'bisect_tester_staging',
    'chromium',
    'chromium_tests',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/step',
]


def RunSteps(api):
  api.path.c.dynamic_paths['bisect_results'] = api.path['start_dir'].join(
      'bisect_results')

  api.chromium.set_config('chromium')

  test = api.chromium_tests.steps.BisectTestStaging()

  test.pre_run(api, '')

  try:
    test.run(api, '')
  finally:
    api.step('details', [])
    api.step.active_result.presentation.logs['details'] = [
        'compile_targets: %r' % test.compile_targets(api),
        'uses_local_devices: %r' % test.uses_local_devices,
    ]


def GenTests(api):
  bisect_config = {
      'test_type': 'perf',
      'command': './tools/perf/run_benchmark -v '
                 '--browser=android-chromium --output-format=valueset '
                 'page_cycler_v2.intl_ar_fa_he',
      'metric': 'warm_times/page_load_time',
      'repeat_count': '2',
      'max_time_minutes': '5',
      'truncate_percent': '25',
      'bug_id': '425582',
      'gs_bucket': 'chrome-perf',
      'builder_host': 'master4.golo.chromium.org',
      'builder_port': '8341'
  }
  yield (
      api.test('basic') +
      api.properties(
          bisect_config=bisect_config,
          buildername='test_buildername',
          bot_id='test_bot_id')
  )
