# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_tests',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
]


def RunSteps(api):
  bot_config = api.chromium_tests.create_bot_config_object([
      api.chromium_tests.create_bot_id(
          api.properties['mastername'], api.properties['buildername'])])
  api.chromium_tests.configure_build(bot_config)
  update_step, bot_db = api.chromium_tests.prepare_checkout(bot_config)
  api.chromium_tests.package_build(
      api.properties['mastername'], api.properties['buildername'],
      update_step, bot_db)


def GenTests(api):
  yield (
      api.test('linux_builder') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Builder')
  )

  yield (
      api.test('linux_perf_builder') +
      api.properties.generic(
          mastername='chromium.perf',
          buildername='linux-builder-perf')
  )
