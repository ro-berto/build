# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromium_android',
  'recipe_engine/buildbucket',
]


def RunSteps(api):
  api.chromium.set_config('chromium')
  api.chromium_android.set_config('try_builder')
  api.chromium_android.logcat_dump('test-bucket')


def GenTests(api):
  yield api.test('basic', api.buildbucket.try_build())
