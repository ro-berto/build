# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/runtime',
]


def RunSteps(api):
  api.chromium.set_config(
      'chromium',
      TARGET_PLATFORM=api.properties.get('target_platform', 'linux'),
      TARGET_CROS_BOARD=api.properties.get('target_cros_board'))
  api.chromium.apply_config('mb')

  api.chromium.runhooks()


def GenTests(api):
  yield api.test('basic')

  yield (
      api.test('chromeos') +
      api.properties(
          target_platform='chromeos',
          target_cros_board='x86-generic')
  )

  yield (
      api.test('clobber') +
      api.properties(clobber='1')
  )

  yield (
      api.test('mac_buildbot') +
      api.platform.name('mac') +
      api.properties(target_platform='mac') +
      api.runtime(is_luci=False, is_experimental=False)
  )
