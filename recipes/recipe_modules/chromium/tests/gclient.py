# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
  'depot_tools/gclient',
  'recipe_engine/properties',
]

TEST_CONFIGS = [
  'android_bare',
  'arm',
  'arm64',
  'blink',
  'chrome_internal',
  'chromedriver',
  'chromium',
  'chromium_lkgr',
  'chromium_perf',
  'chromium_skia',
  'chromium_webrtc',
  'chromium_webrtc_tot',
  'fuchsia',
  'ios',
  'ndk_next',
  'openscreen_tot',
  'perf',
  'show_v8_revision',
  'v8_canary',
  'v8_tot',
  'webrtc_test_resources',
  'win',
]


def RunSteps(api):
  for config_name in TEST_CONFIGS:
    api.gclient.make_config(config_name)

  api.gclient.set_config('chromium')
  api.gclient.apply_config(api.properties.get('apply_gclient_config'))

def GenTests(api):
  yield api.test(
      'basic',
      api.properties(apply_gclient_config='checkout_instrumented_libraries'),
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'clang_coverage',
      api.properties(apply_gclient_config='use_clang_coverage'),
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'pgo_profiles',
      api.properties(apply_gclient_config='checkout_pgo_profiles'),
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'enable_wpr_tests',
      api.properties(apply_gclient_config='enable_wpr_tests'),
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'chromium_skip_wpr_archives_download',
      api.properties(
          apply_gclient_config='chromium_skip_wpr_archives_download'),
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'chromium_skip_render_test_goldens_download',
      api.properties(
          apply_gclient_config='chromium_skip_render_test_goldens_download'),
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'clang_tidy',
      api.properties(apply_gclient_config='use_clang_tidy'),
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'tot_clang',
      api.properties(apply_gclient_config='clang_tot'),
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'ios_webkit_tot',
      api.properties(apply_gclient_config='ios_webkit_tot'),
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'no_checkout_flash',
      api.properties(apply_gclient_config='no_checkout_flash'),
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'no_kaleidoscope',
      api.properties(apply_gclient_config='no_kaleidoscope'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'enable_soda',
      api.properties(apply_gclient_config='enable_soda'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'android_prebuilts_build_tools',
      api.properties(apply_gclient_config='android_prebuilts_build_tools'),
      api.post_process(post_process.DropExpectation),
  )
