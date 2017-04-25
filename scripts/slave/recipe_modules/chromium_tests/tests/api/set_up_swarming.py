# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_tests',
    'recipe_engine/platform',
    'recipe_engine/properties',
]


def RunSteps(api):
  bot_config_object = api.chromium_tests.create_bot_config_object(
      api.properties['mastername'], api.properties['buildername'])
  api.chromium_tests.set_up_swarming(bot_config_object)


def GenTests(api):
  yield (
      api.test('basic') +
      api.platform.name('win') +
      api.properties.generic(
          mastername='chromium.win',
          buildername='Win10 Tests x64')
  )
