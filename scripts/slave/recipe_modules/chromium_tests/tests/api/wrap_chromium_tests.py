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
    tests.append(api.chromium_tests.steps.SwarmingGTestTest(
        'base_unittests',
        set_up=[{'name': 'set_up', 'script': 'set_up_script', 'args': []}],
        tear_down=[{'name': 'tear_down', 'script': 'tear_down_script',
                    'args': []}]))
  if api.properties.get('local_isolated_script_test'):
    tests.append(api.chromium_tests.steps.LocalIsolatedScriptTest(
        'base_unittests',
        set_up=[{'name': 'set_up', 'script': 'set_up_script', 'args': []}],
        tear_down=[{'name': 'tear_down', 'script': 'tear_down_script',
                    'args': []}],
        override_compile_targets=['base_unittests_run']))
  if api.properties.get('script_test'):
    tests.append(api.chromium_tests.steps.ScriptTest(
        'script_test',
        'script.py',
        {'script.py': ['compile_target']},
        script_args=['some', 'args'],
        override_compile_targets=['other_target']))
  if api.properties.get('instrumentation_test'):
    tests.append(api.chromium_tests.steps.AndroidInstrumentationTest(
        'sample_android_instrumentation_test',
        set_up=[{'name': 'set_up', 'script': 'set_up_script', 'args': []}],
        tear_down=[{'name': 'tear_down',
                    'script': 'tear_down_script', 'args': []}]))
  if api.tryserver.is_tryserver:
    trybot_config = api.chromium_tests.trybots[
        api.properties['mastername']]['builders'][api.properties['buildername']]
    bot_ids = trybot_config['bot_ids']
  else:
    bot_ids = [
        api.chromium_tests.create_bot_id(
            api.properties['mastername'], api.properties['buildername'])
    ]
  bot_config_object = api.chromium_tests.create_bot_config_object(bot_ids)
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
          mastername='chromium.android',
          buildername='KitKat Phone Tester (rel)')
  )

  yield (
      api.test('no_require_device_steps_with_root') +
      api.properties.generic(
          mastername='chromium.fyi',
          buildername='Android Remoting Tests')
  )

  yield (
      api.test('win') +
      api.platform.name('win') +
      api.properties.tryserver(
          mastername='tryserver.chromium.win',
          buildername='win7_chromium_rel_ng')
  )

  yield (
      api.test('isolated_targets') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests',
          swarming_gtest=True)
  )

  yield (
      api.test('local_isolated_script_test') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests',
          local_isolated_script_test=True,)
  )

  yield (
      api.test('script_test') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests',
          script_test=True)
  )

  yield (
      api.test('instrumentation_test') +
      api.properties.generic(
          mastername='chromium.fyi',
          buildername='Android VR Tests',
          instrumentation_test=True)
  )
