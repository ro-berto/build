# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_android',
    'chromium_tests',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/step',
]


def RunSteps(api):
  api.chromium.set_config('chromium')
  api.chromium_android.set_config('main_builder')

  if api.properties.get('platform') == 'android':
    api.chromium_android.device_status_check()

  test = api.chromium_tests.steps.DynamicPerfTests(
      perf_id='test-perf-id',
      platform=api.properties.get('platform', 'linux'),
      target_bits=64,
      num_device_shards=api.properties.get('num_device_shards', 1),
      replace_webview=True)

  try:
    test.run(api, '')
  finally:
    api.step('details', [])
    api.step.active_result.presentation.logs['details'] = [
        'compile_targets: %r' % test.compile_targets(api),
        'uses_local_devices: %r' % test.uses_local_devices,
    ]


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(
          buildername='test_buildername',
          bot_id='test_bot_id')
  )

  yield (
      api.test('sharded') +
      api.properties(
          buildername='test_buildername',
          bot_id='test_bot_id',
          buildnumber=123,
          platform='android',
          num_device_shards=2)
  )
