# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/runtime',
]


def RunSteps(api):
  api.chromium.set_config(
      api.properties.get('chromium_config', 'chromium'),
      TARGET_PLATFORM=api.properties.get('target_platform', 'linux'))

  for config in api.properties.get('chromium_apply_config', []):
    api.chromium.apply_config(config)

  kwargs = {}
  if api.properties.get('annotate'):
    kwargs.update({
        'annotate': api.properties.get(
            'annotate',
            api.chromium.get_annotate_by_test_name('base_unittests')),
        'args': [api.chromium.test_launcher_filter('AtExit*')],
        'test_launcher_summary_output': api.json.output(),
    })
  elif api.properties.get('use_histograms', False):
    kwargs.update({
        'use_histograms': True,
    })
  else:
    kwargs.update({
        'chartjson_file': True,
    })

  api.chromium.runtest(
      'base_unittests',
      python_mode=api.properties.get('python_mode', False),
      point_id=123456,
      revision='some_sha',
      test_type='base_unittests',
      results_url='https://example/url',
      perf_dashboard_id='test_perf_dashboard_id',
      perf_id='test_perf_id',
      perf_config={'a_default_rev': 'some_sha'},
      tee_stdout_file=api.path['tmp_base'].join('stdout.log'),
      **kwargs)


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id')
  )

  yield (
      api.test('histograms') +
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          use_histograms=True)
  )

  yield (
      api.test('android') +
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          target_platform='android') +
      api.runtime(is_luci=False, is_experimental=False)
  )

  # In order to get coverage of the LUCI-specific code in runtest.
  yield (
      api.test('luci') +
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          target_platform='android') +
      api.runtime(is_luci=True, is_experimental=False)
  )

  yield (
      api.test('win') +
      api.platform('win', 64) +
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          target_platform='win')
  )

  yield (
      api.test('annotate') +
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          annotate='gtest')
  )

  yield (
      api.test('python_mode') +
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          python_mode=True)
  )

  yield (
      api.test('memcheck') +
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          chromium_apply_config=['memcheck'])
  )

  yield (
      api.test('tsan') +
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          chromium_config='chromium_clang',
          chromium_apply_config=['tsan2'])
  )

  yield (
      api.test('msan') +
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          chromium_config='chromium_msan')
  )

  yield (
      api.test('lsan') +
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          chromium_config='chromium_clang',
          chromium_apply_config=['lsan'])
  )

  yield (
      api.test('asan') +
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          chromium_apply_config=['chromium_win_asan'])
  )
