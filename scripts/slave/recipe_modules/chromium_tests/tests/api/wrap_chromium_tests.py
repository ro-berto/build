# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_tests',
    'depot_tools/tryserver',
    'recipe_engine/platform',
    'recipe_engine/properties',
]


def RunSteps(api):
  tests = []
  if api.properties.get('local_gtest'):
    tests.append(api.chromium_tests.steps.LocalGTestTest('base_unittests'))
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
  with api.chromium_tests.wrap_chromium_tests(bot_config_object, tests=tests):
    pass


def GenTests(api):
  yield (
      api.test('require_device_steps') +
      api.properties.tryserver(
          mastername='tryserver.chromium.android',
          buildername='android_blink_rel',
          local_gtest=True)
  )

  yield (
      api.test('no_require_device_steps') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Android Tests')
  )

  yield (
      api.test('win') +
      api.platform.name('win') +
      api.properties.tryserver(
          mastername='tryserver.chromium.win',
          buildername='win_chromium_rel_ng')
  )

  yield (
      api.test('isolated_targets') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests',
          swarming_gtest=True)
  )
