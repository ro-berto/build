# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/step',
]


def RunSteps(api):
  api.chromium.set_config('chromium', TARGET_PLATFORM='mac')
  for config in api.properties.get('chromium_apply_config', []):
    api.chromium.apply_config(config)

  api.chromium.c.env.ADB_VENDOR_KEYS = api.path['start_dir'].join('.adb_key')

  with api.context(env=api.chromium.get_env()):
    api.step('test', [])


def GenTests(api):
  yield (
      api.test('basic') +
      api.platform('mac', 64)
  )

  yield (
      api.test('mac_force_toolchain_off_10_10') +
      api.platform('mac', 64) +
      api.properties(chromium_apply_config=['force_mac_toolchain_off_10_10'])
  )

  yield (
      api.test('mac_force_toolchain_off_10_11') +
      api.platform('mac', 64) +
      api.properties(chromium_apply_config=['force_mac_toolchain_off_10_11'])
  )

  yield (
      api.test('clang_tot') +
      api.platform('mac', 64) +
      api.properties(chromium_apply_config=['clang_tot'])
  )

  yield (
      api.test('force_mac_toolchain_override') +
      api.platform('mac', 64) +
      api.properties(chromium_apply_config=['force_mac_toolchain_override'])
  )

  yield (
      api.test('goma_staging') +
      api.platform('mac', 64) +
      api.properties(chromium_apply_config=['goma_staging'])
  )

  yield (
      api.test('goma_gce') +
      api.platform('mac', 64) +
      api.properties(chromium_apply_config=['goma_gce'])
  )
