# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'goma',
  'recipe_engine/properties',
  'recipe_engine/runtime',
]


def RunSteps(api):
  api.chromium.set_config(
      api.properties.get('chromium_config', 'chromium_clang'),
      TARGET_PLATFORM=api.properties.get('target_platform', 'linux'),
      TARGET_CROS_BOARD=api.properties.get('target_cros_board'))
  api.chromium.apply_config('goma_hermetic_fallback')
  api.chromium.apply_config('goma_high_parallel')
  api.chromium.apply_config('goma_localoutputcache')
  api.chromium.apply_config('goma_enable_global_file_id_cache')

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

  yield (
      api.test('goma_canary') +
      api.properties(
          buildername='test_buildername',
          chromium_apply_config=['goma_canary'])
  )

  yield (
      api.test('goma_localoutputcache_small') +
      api.properties(
          buildername='test_buildername',
          chromium_apply_config=['goma_localoutputcache_small'])
  )

  yield (
      api.test('goma_custom_jobs_debug') +
      api.properties(buildername='test_buildername') +
      api.goma(jobs=500, debug=True) + api.runtime(is_luci=True, is_experimental=False)
  )
