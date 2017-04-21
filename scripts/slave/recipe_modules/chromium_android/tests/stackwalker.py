# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromium_android',
  'recipe_engine/path',
]


def RunSteps(api):
  api.chromium.set_config('chromium')
  api.chromium_android.stackwalker(
      api.path['checkout'],
      [api.chromium.output_dir.join('lib.unstripped', 'libchrome.so')])


def GenTests(api):
  yield api.test('basic')
