# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromium_android',
  'recipe_engine/path',
  'recipe_engine/properties',
]


def RunSteps(api):
  api.chromium.set_config('chromium')
  api.chromium_android.set_config('main_builder')
  api.chromium_android.resource_sizes(
      apk_path=api.path['start_dir'].join('test.apk'),
      estimate_patch_size=True)


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id')
  )
