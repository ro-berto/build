# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromium_android',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/step',
]


def RunSteps(api):
  api.chromium.set_config('chromium_clang')
  api.chromium.apply_config('asan')
  api.chromium_android.set_config('main_builder')
  with api.chromium_android.android_build_wrapper()(api):
    pass


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(buildername='test_buildername', buildnumber=123)
  )
