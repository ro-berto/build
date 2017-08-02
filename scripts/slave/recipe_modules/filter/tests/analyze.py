# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'filter',
  'recipe_engine/platform',
  'recipe_engine/properties',
]


def RunSteps(api):
  if api.properties.get('config', '') == 'cros':
    api.chromium.set_config(
      'chromium_chromeos',
      TARGET_PLATFORM='chromeos',
      TARGET_CROS_BOARD='x86=generic')
  else:
    api.chromium.set_config('chromium')
  api.chromium.apply_config('mb')
  for config in api.properties.get('chromium_apply_config', []):
    api.chromium.apply_config(config)

  api.filter.analyze(
      ['file1', 'file2'],
      ['test1', 'test2'],
      ['compile1', 'compile2'],
      'config.json')


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          config='cros')
  )
  yield (
      api.test('basic_mac') +
      api.platform('mac', 64) +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          chromium_apply_config=['force_mac_toolchain_off_10_10'])
  )
