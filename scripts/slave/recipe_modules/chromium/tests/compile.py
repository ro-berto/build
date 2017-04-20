# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'recipe_engine/properties',
]


def RunSteps(api):
  api.chromium.set_config(
      api.properties.get('chromium_config', 'chromium_clang'),
      TARGET_PLATFORM=api.properties.get('target_platform', 'linux'),
      TARGET_CROS_BOARD=api.properties.get('target_cros_board'))
  api.chromium.apply_config('goma_hermetic_fallback')
  api.chromium.apply_config('goma_high_parallel')
  api.chromium.apply_config('goma_linktest')
  api.chromium.apply_config('goma_localoutputcache')

  for config in api.properties.get('chromium_apply_config', []):
    api.chromium.apply_config(config)

  api.chromium.c.compile_py.goma_max_active_fail_fallback_tasks = 1
  api.chromium.ensure_goma()
  api.chromium.compile(use_goma_module=True)


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(buildername='test_buildername')
  )

  yield (
      api.test('codesearch') +
      api.properties(
          buildername='test_buildername',
          chromium_apply_config=['codesearch'])
  )

  yield (
      api.test('official') +
      api.properties(
          buildername='test_buildername',
          chromium_apply_config=['official'])
  )

  yield (
      api.test('chromeos') +
      api.properties(
          buildername='test_buildername',
          target_platform='chromeos',
          target_cros_board='x86-generic')
  )
