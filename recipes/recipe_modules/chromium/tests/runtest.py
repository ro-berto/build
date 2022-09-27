# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.build.chromium_tests.steps import ResultDB

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
  if api.properties.get('parse_gtest_output'):
    kwargs.update({
        'parse_gtest_output': True,
        'test_launcher_summary_output': api.json.output(),
    })

  if api.properties.get('resultdb'):
    kwargs['resultdb'] = ResultDB.create(enable=True)

  api.chromium.runtest(
      'base_unittests',
      builder_group=api.properties.get('builder_group'),
      python_mode=api.properties.get('python_mode', False),
      test_type='base_unittests',
      **kwargs)


def GenTests(api):
  yield api.test(
      'basic',
      api.properties(
          buildername='test_buildername', buildnumber=123,
          bot_id='test_bot_id'),
  )

  yield api.test(
      'resultdb',
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          resultdb=True),
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
  )

  # In order to get coverage of the LUCI-specific code in runtest.
  yield api.test(
      'android',
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          target_platform='android'),
  )

  yield api.test(
      'win',
      api.platform('win', 64),
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          target_platform='win'),
  )

  yield api.test(
      'builder_group',
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          builder_group='fake-builder-group'),
  )

  yield api.test(
      'parse_gtest_output',
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          parse_gtest_output=True),
  )

  yield api.test(
      'python_mode',
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          python_mode=True),
  )

  yield api.test(
      'memcheck',
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          chromium_apply_config=['memcheck']),
  )

  yield api.test(
      'tsan',
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          chromium_config='chromium_clang',
          chromium_apply_config=['tsan2']),
  )

  yield api.test(
      'msan',
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          chromium_config='chromium_msan'),
  )

  yield api.test(
      'lsan',
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          chromium_config='chromium_clang',
          chromium_apply_config=['lsan']),
  )

  yield api.test(
      'asan',
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          chromium_apply_config=['chromium_win_asan']),
  )
