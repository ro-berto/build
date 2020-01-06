# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import steps

DEPS = [
    'chromium',
    'chromium_tests',
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
    'recipe_engine/platform',
    'recipe_engine/properties',
]


def RunSteps(api):
  tests = []
  if api.properties.get('local_gtest'):
    tests.append(steps.LocalGTestTest('base_unittests'))
  if api.properties.get('swarming_gtest'):
    tests.append(
        steps.SwarmingGTestTest(
            'base_unittests',
            set_up=[{
                'name': 'set_up',
                'script': 'set_up_script',
                'args': []
            }],
            tear_down=[{
                'name': 'tear_down',
                'script': 'tear_down_script',
                'args': []
            }]))
  if api.properties.get('local_isolated_script_test'):
    tests.append(
        steps.LocalIsolatedScriptTest(
            'base_unittests',
            set_up=[{
                'name': 'set_up',
                'script': 'set_up_script',
                'args': []
            }],
            tear_down=[{
                'name': 'tear_down',
                'script': 'tear_down_script',
                'args': []
            }],
            override_compile_targets=['base_unittests_run']))
  if api.properties.get('script_test'):
    tests.append(
        steps.ScriptTest(
            'script_test',
            'script.py', {'script.py': ['compile_target']},
            script_args=['some', 'args'],
            override_compile_targets=['other_target']))
  if api.tryserver.is_tryserver:
    trybot_config = api.chromium_tests.trybots[
        api.properties['mastername']]['builders'][api.buildbucket.builder_name]
    bot_ids = trybot_config['bot_ids']
  else:
    bot_ids = [
        api.chromium_tests.create_bot_id(
            api.properties['mastername'], api.properties['buildername'])
    ]
  bot_config_object = api.chromium_tests.create_bot_config_object(
      bot_ids,
      builders=api.properties.get('builders') or api.chromium_tests.builders)
  api.chromium_tests.configure_build(bot_config_object)
  with api.chromium_tests.wrap_chromium_tests(bot_config_object, tests=tests):
    pass


def GenTests(api):

  test_builders = {
      'chromium.example': {
          'builders': {
              'android-basic': {
                  'android_config': 'main_builder',
                  'chromium_apply_config': [
                      'mb',
                  ],
                  'chromium_config': 'android',
                  'chromium_config_kwargs': {
                      'BUILD_CONFIG': 'Release',
                      'TARGET_BITS': 32,
                      'TARGET_PLATFORM': 'android',
                  },
                  'gclient_config': 'chromium',
                  'gclient_apply_config': ['android'],
                  'bot_type': 'builder_tester',
                  'testing': {
                      'platform': 'linux',
                  },
              },
          },
      },
  }

  yield api.test(
      'require_device_steps',
      api.properties.generic(
          mastername='chromium.example',
          buildername='android-basic',
          local_gtest=True,
          builders=test_builders),
      api.post_process(post_process.MustRun, 'device_recovery'),
      api.post_process(post_process.MustRun, 'provision_devices'),
      api.post_process(post_process.MustRun, 'device_status'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'use_clang_coverage',
      api.properties.generic(
          mastername='chromium.fyi', buildername='linux-code-coverage'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'win',
      api.platform.name('win'),
      api.chromium.try_build(
          mastername='tryserver.chromium.win', builder='win7-rel'),
  )

  yield api.test(
      'isolated_targets',
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests',
          swarming_gtest=True),
  )

  yield api.test(
      'local_isolated_script_test',
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests',
          local_isolated_script_test=True,
      ),
  )

  yield api.test(
      'script_test',
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests',
          script_test=True),
  )
