# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import DropExpectation

DEPS = [
  'depot_tools/gclient',
]

TEST_CONFIGS = [
  'android_bare',
  'blink',
  'chrome_internal',
  'chromedriver',
  'chromium',
  'chromium_lkcr',
  'chromium_lkgr',
  'chromium_perf',
  'chromium_perf_android',
  'chromium_skia',
  'chromium_webrtc',
  'chromium_webrtc_tot',
  'ios',
  'ndk_next',
  'perf',
  'show_v8_revision',
  'v8_bleeding_edge_git',
  'v8_canary',
  'webrtc_test_resources',
]


def RunSteps(api):
  for config_name in TEST_CONFIGS:
    api.gclient.make_config(config_name)


def GenTests(api):
  yield api.test('basic') + api.post_process(DropExpectation)
