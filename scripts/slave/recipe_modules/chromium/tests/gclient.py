# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import DropExpectation

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
  yield (
      api.test('basic') +
      api.properties(apply_gclient_config='checkout_instrumented_libraries') +
      api.post_process(DropExpectation)
  )
  yield (
      api.test('clang_coverage') +
      api.properties(apply_gclient_config='use_clang_coverage') +
      api.post_process(DropExpectation)
  )
  yield (
      api.test('tot_clang') +
      api.properties(apply_gclient_config='use_tot_clang') +
      api.post_process(DropExpectation)
  )

