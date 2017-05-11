# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/step',
]


def RunSteps(api):
  api.chromium.set_config('chromium', TARGET_PLATFORM='mac')
  api.chromium.apply_config('clang_tot')
  api.chromium.apply_config('force_mac_toolchain_override')
  api.chromium.apply_config('goma_staging')

  api.chromium.c.env.ADB_VENDOR_KEYS = api.path['start_dir'].join('.adb_key')

  with api.context(env=api.chromium.get_env()):
    api.step('test', [])


def GenTests(api):
  yield (
      api.test('basic') +
      api.platform('mac', 64)
  )
