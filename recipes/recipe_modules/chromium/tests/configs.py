# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process


PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'chromium',
    'recipe_engine/platform',
    'recipe_engine/properties',
]


def RunSteps(api):
  api.chromium.set_config(
      api.properties.get('chromium_config', 'chromium'),
      TARGET_PLATFORM=api.properties.get('target_platform', 'linux'),
      TARGET_BITS=api.properties.get('target_bits', 64))

  for config in api.properties.get('chromium_apply_config', []):
    api.chromium.apply_config(config)


def GenTests(api):
  def from_config(config):
    return api.test(
        config,
        api.properties(chromium_config=config),
        api.post_process(post_process.StatusSuccess),
        api.post_process(post_process.DropExpectation),
    )

  yield from_config('gn')

  yield api.test(
      'ios',
      api.platform('mac', 64),
      api.properties(target_platform='ios'),
      api.post_process(post_process.DropExpectation),
  )

  yield from_config('goma_canary')

  yield from_config('goma_latest_client')

  yield from_config('goma_use_local')

  yield from_config('goma_large_cache_file')

  yield from_config('gcc')

  yield from_config('trybot_flavor')

  yield api.test(
      'chromium_win_clang_official',
      api.platform('win', 64),
      api.properties(
          chromium_config='chromium_win_clang_official', target_platform='win'),
      api.post_process(post_process.DropExpectation),
  )

  yield from_config('chromium_win_clang_official_tot')

  yield from_config('chromium_win_clang_asan')

  yield from_config('chromium_win_clang_asan_tot')

  yield from_config('clang_tot_linux')

  yield api.test(
      'clang_tot_mac',
      api.platform('mac', 64),
      api.properties(
          chromium_config='clang_tot_mac_asan', target_platform='mac'),
      api.post_process(post_process.DropExpectation),
  )

  yield from_config('clang_tot_linux_asan')

  yield from_config('chromium_linux_ubsan')

  yield from_config('chromium_linux_ubsan_vptr')

  yield from_config('clang_tot_linux_ubsan_vptr')

  yield api.test(
      'clang_tot_mac_asan',
      api.platform('mac', 64),
      api.properties(
          chromium_config='clang_tot_mac_asan', target_platform='mac'),
      api.post_process(post_process.DropExpectation),
  )

  yield from_config('clang_tot_android_asan')

  yield from_config('clang_tot_android_dbg')

  yield from_config('clang_tot_chromeos')

  yield from_config('clang_tot_fuchsia')

  yield from_config('chromium_tsan2')

  yield from_config('android_clang')

  yield from_config('android_asan')

  yield from_config('download_vr_test_apks')

  yield api.test(
      'mac_toolchain',
      api.platform('mac', 64),
      api.properties(
          target_platform='mac',
          chromium_apply_config=['mac_toolchain'],
      ),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'ios_toolchain',
      api.platform('mac', 64),
      api.properties(
          target_platform='ios',
          chromium_apply_config=['mac_toolchain'],
      ),
      api.post_process(post_process.DropExpectation),
  )

  yield from_config('android_internal_isolate_maps')

  yield from_config('official_no_clobber')
