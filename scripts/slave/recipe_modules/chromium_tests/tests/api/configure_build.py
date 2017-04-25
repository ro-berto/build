# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process


DEPS = [
    'chromium_tests',
    'recipe_engine/platform',
    'recipe_engine/properties',
]


def RunSteps(api):
  bot_config_object = api.chromium_tests.create_bot_config_object(
      api.properties['mastername'], api.properties['buildername'])
  api.chromium_tests.configure_build(bot_config_object)


def GenTests(api):
  yield (
      api.test('set_component_rev') +
      api.properties.generic(
          mastername='client.v8.fyi',
          buildername='Linux Tests (dbg)(1)') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('android_apply_config') +
      api.properties.generic(
          mastername='chromium.android',
          buildername='KitKat Tablet Tester') +
      api.post_process(post_process.DropExpectation)
  )
