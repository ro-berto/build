# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
  'chromium',
  'filter',
  'recipe_engine/platform',
  'recipe_engine/properties',
]


def RunSteps(api):
  api.chromium.set_config(
    'chromium_chromeos',
    TARGET_PLATFORM='chromeos',
    TARGET_CROS_BOARD='x86-generic')
  if api.properties.get('gn', False):
    api.chromium.apply_config('gn')
  else:
    api.chromium.apply_config('mb')

  api.filter.analyze(
      ['file1', 'file2'],
      ['test1', 'test2'],
      ['compile1', 'compile2'],
      'config.json',
      mb_mastername=api.properties.get('mastername'),
      mb_buildername=api.properties.get('buildername'),
      mb_config_path=api.properties.get('mb_config_path'))


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          config='cros')
  )

  yield (
      api.test('custom_mb_config_path') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          mb_config_path='path/to/custom_mb_config.pyl',
          config='cros') +
      api.post_process(
          post_process.StepCommandContains,
          'analyze',
          ['--config-file', 'path/to/custom_mb_config.pyl']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('cros_no_mb') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          config='cros',
          gn=True) +
      api.post_process(
          post_process.MustRun,
          'system_python') +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation)
  )
