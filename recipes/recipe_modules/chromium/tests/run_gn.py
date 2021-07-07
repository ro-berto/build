# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'recipe_engine/platform',
  'recipe_engine/properties',
]


def RunSteps(api):
  api.chromium.set_config(
      api.properties.get('chromium_config', 'chromium'),
      BUILD_CONFIG=api.properties.get('build_config', 'Release'),
      TARGET_PLATFORM=api.properties.get('target_platform', 'linux'))

  use_rbe = api.properties.get('use_rbe', False)
  use_goma = not use_rbe

  api.chromium.run_gn(
      use_goma=use_goma,
      gn_path=api.properties.get('gn_path'),
      use_reclient=use_rbe)


def GenTests(api):
  yield api.test('basic')

  yield api.test(
      'custom_gn_path',
      api.properties(gn_path='some/other/path/gn'),
  )

  yield api.test(
      'mac',
      api.platform('mac', 64),
      api.properties(target_platform='mac'),
  )

  yield api.test(
      'android',
      api.properties(target_platform='android'),
  )

  yield api.test(
      'debug',
      api.properties(build_config='Debug'),
  )

  yield api.test(
      'reclient',
      api.properties(build_config='Debug', use_rbe=True),
  )
