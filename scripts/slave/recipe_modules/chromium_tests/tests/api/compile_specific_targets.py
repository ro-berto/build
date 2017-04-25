# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_tests',
    'depot_tools/tryserver',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
]


def RunSteps(api):
  tests = []
  if api.properties.get('swarming_gtest'):
    tests.append(api.chromium_tests.steps.SwarmingGTestTest('base_unittests'))

  if api.tryserver.is_tryserver:
    bot_config = api.chromium_tests.trybots[
        api.properties['mastername']]['builders'][api.properties['buildername']]
    bot_config_object = api.chromium_tests.create_generalized_bot_config_object(
        bot_config['bot_ids'])
  else:
    bot_config_object = api.chromium_tests.create_bot_config_object(
        api.properties['mastername'], api.properties['buildername'])
  api.chromium_tests.configure_build(bot_config_object)
  update_step, bot_db = api.chromium_tests.prepare_checkout(bot_config_object)
  api.chromium_tests.compile_specific_targets(
      bot_config_object, update_step, bot_db,
      compile_targets=['base_unittests'],
      tests_including_triggered=tests,
      override_bot_type='builder_tester')


def GenTests(api):
  yield (
      api.test('linux_tests') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests',
          swarming_gtest=True)
  )

  yield (
      api.test('failure') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests',
          swarming_gtest=True) +
      api.override_step_data('compile', retcode=1)
  )

  yield (
      api.test('failure_tryserver') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng') +
      api.override_step_data('compile (with patch)', retcode=1)
  )

  yield (
      api.test('perf_isolate_lookup') +
      api.properties.generic(
          mastername='chromium.perf',
          buildername='Linux Builder',
          swarming_gtest=True)
  )

  yield (
      api.test('update_clang') +
      api.platform.name('win') +
      api.properties.generic(
          mastername='chromium.win',
          buildername='WinClang64 (dbg)')
  )

  yield (
      api.test('android') +
      api.properties.generic(
          mastername='chromium.android',
          buildername='Android Cronet Builder')
  )
