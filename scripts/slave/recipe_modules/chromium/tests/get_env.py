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

  with api.context(env=api.chromium.get_env()):
    api.step('test', [])


def GenTests(api):
  yield (
      api.test('basic') +
      api.platform('mac', 64)
  )

  yield (
      api.test('clang_tot') +
      api.platform('mac', 64) +
      api.properties(chromium_apply_config=['clang_tot'])
  )

  yield (
      api.test('goma_staging') +
      api.platform('mac', 64) +
      api.properties(chromium_apply_config=['goma_staging'])
  )

  yield (
      api.test('goma_rbe_tot') +
      api.platform('mac', 64) +
      api.properties(chromium_apply_config=['goma_rbe_tot'])
  )

  yield (
      api.test('goma_mixer_staging') +
      api.platform('mac', 64) +
      api.properties(chromium_apply_config=['goma_mixer_staging'])
  )

  yield (
      api.test('goma_rbe_prod') +
      api.platform('mac', 64) +
      api.properties(chromium_apply_config=['goma_rbe_prod'])
  )

  yield (
      api.test('goma_store_only') +
      api.platform('mac', 64) +
      api.properties(chromium_apply_config=['goma_store_only'])
  )
