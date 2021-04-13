# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec, steps

DEPS = [
    'chromium',
    'chromium_tests',
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
]


def RunSteps(api):
  test_specs = []
  if api.properties.get('local_gtest'):
    test_specs.append(steps.LocalGTestTestSpec.create('base_unittests'))
  if api.properties.get('swarming_gtest'):
    test_specs.append(
        steps.SwarmingGTestTestSpec.create(
            'base_unittests',
            set_up=[
                steps.SetUpScript.create(
                    name='set_up',
                    script=api.path['cache'].join('set_up_script'),
                    args=[])
            ],
            tear_down=[
                steps.TearDownScript.create(
                    name='tear_down',
                    script=api.path['cache'].join('tear_down_script'),
                    args=[])
            ]))
  if api.properties.get('local_isolated_script_test'):
    test_specs.append(
        steps.LocalIsolatedScriptTestSpec.create(
            'base_unittests',
            set_up=[
                steps.SetUpScript.create(
                    name='set_up',
                    script=api.path['cache'].join('set_up_script'),
                    args=[])
            ],
            tear_down=[
                steps.TearDownScript.create(
                    name='tear_down',
                    script=api.path['cache'].join('tear_down_script'),
                    args=[])
            ],
            override_compile_targets=['base_unittests_run']))
  if api.properties.get('script_test'):
    test_specs.append(
        steps.ScriptTestSpec.create(
            'script_test',
            script='script.py',
            all_compile_targets={'script.py': ['compile_target']},
            script_args=['some', 'args'],
            override_compile_targets=['other_target']))
  _, bot_config = api.chromium_tests.lookup_builder()
  api.chromium_tests.configure_build(bot_config)
  tests = [s.get_test() for s in test_specs]
  with api.chromium_tests.wrap_chromium_tests(bot_config, tests=tests):
    pass


def GenTests(api):
  test_builders = bot_db.BotDatabase.create({
      'chromium.example': {
          'android-basic':
              bot_spec.BotSpec.create(
                  android_config='main_builder',
                  chromium_apply_config=[
                      'mb',
                  ],
                  chromium_config='android',
                  chromium_config_kwargs={
                      'BUILD_CONFIG': 'Release',
                      'TARGET_BITS': 32,
                      'TARGET_PLATFORM': 'android',
                  },
                  gclient_config='chromium',
                  gclient_apply_config=['android'],
                  simulation_platform='linux',
              ),
      },
  })

  yield api.test(
      'require_device_steps',
      api.chromium.ci_build(
          builder_group='chromium.example', builder='android-basic'),
      api.chromium_tests.builders(test_builders),
      api.properties(local_gtest=True),
      api.post_process(post_process.MustRun, 'device_recovery'),
      api.post_process(post_process.MustRun, 'provision_devices'),
      api.post_process(post_process.MustRun, 'device_status'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'use_clang_coverage',
      api.chromium.ci_build(
          builder_group='chromium.fyi', builder='linux-code-coverage'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'win',
      api.platform.name('win'),
      api.chromium.try_build(
          builder_group='tryserver.chromium.win', builder='win7-rel'),
  )

  yield api.test(
      'isolated_targets',
      api.chromium.ci_build(
          builder_group='chromium.linux', builder='Linux Tests'),
      api.properties(swarming_gtest=True),
  )

  yield api.test(
      'local_isolated_script_test',
      api.chromium.ci_build(
          builder_group='chromium.linux', builder='Linux Tests'),
      api.properties(local_isolated_script_test=True,),
  )

  yield api.test(
      'script_test',
      api.chromium.ci_build(
          builder_group='chromium.linux', builder='Linux Tests'),
      api.properties(script_test=True),
  )
