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
  bot_config = api.chromium_tests.create_bot_config_object(
      api.properties['mastername'], api.properties['buildername'])
  api.chromium_tests.configure_build(bot_config)
  update_step, bot_db = api.chromium_tests.prepare_checkout(bot_config)
  api.chromium_tests.archive_build(
      api.properties['mastername'], api.properties['buildername'],
      update_step, bot_db)


def GenTests(api):
  yield (
      api.test('linux_builder') +
      api.properties.generic(
          mastername='chromium.perf',
          buildername='Linux Builder Perf')
  )

  yield (
      api.test('linux_perf_bisect_builder') +
      api.properties.tryserver(
          mastername='tryserver.chromium.perf',
          buildername='linux_perf_bisect_builder')
  )

  yield (
      api.test('cf_archive_build') +
      api.properties.generic(
          mastername='chromium.lkgr',
          buildername='ASAN Release')
  )

  yield (
      api.test('archive_build') +
      api.properties.generic(
          mastername='chromium',
          buildername='Linux x64')
  )

  yield (
      api.test('cross_master_trigger') +
      api.platform.name('win') +
      api.properties.generic(
          mastername='chromium.perf',
          buildername='Win x64 Builder Perf')
  )
