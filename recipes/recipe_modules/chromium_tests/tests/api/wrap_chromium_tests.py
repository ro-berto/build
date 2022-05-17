# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import steps
from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
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
  _, builder_config = api.chromium_tests_builder_config.lookup_builder()
  api.chromium_tests.configure_build(builder_config)
  tests = [s.get_test(api.chromium_tests) for s in test_specs]
  with api.chromium_tests.wrap_chromium_tests(builder_config, tests=tests):
    pass


def GenTests(api):
  ctbc_api = api.chromium_tests_builder_config

  test_builders = ctbc.BuilderDatabase.create({
      'chromium.example': {
          'android-basic':
              ctbc.BuilderSpec.create(
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
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.example',
          builder='android-basic',
          builder_db=test_builders),
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
      api.platform('win', 64),
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
      ),
      ctbc_api.properties(
          ctbc_api.properties_assembler_for_try_builder().with_mirrored_builder(
              builder_group='fake-group',
              builder='fake-builder',
          ).assemble()),
  )

  yield api.test(
      'isolated_targets',
      api.platform('linux', 64),
      api.chromium.ci_build(
          builder_group='fake-group',
          builder='fake-tester',
          parent_buildername='fake-builder'),
      ctbc_api.properties(
          ctbc_api.properties_assembler_for_ci_tester(
              builder_group='fake-group',
              builder='fake-tester',
          ).with_parent(
              builder_group='fake-group',
              builder='fake-builder',
          ).assemble()),
      api.properties(swarming_gtest=True),
  )

  yield api.test(
      'local_isolated_script_test',
      api.platform('linux', 64),
      api.chromium.ci_build(
          builder_group='fake-group',
          builder='fake-tester',
          parent_buildername='fake-builder'),
      ctbc_api.properties(
          ctbc_api.properties_assembler_for_ci_tester(
              builder_group='fake-group',
              builder='fake-tester',
          ).with_parent(
              builder_group='fake-group',
              builder='fake-builder',
          ).assemble()),
      api.properties(local_isolated_script_test=True,),
  )

  yield api.test(
      'script_test',
      api.platform('linux', 64),
      api.chromium.ci_build(
          builder_group='fake-group',
          builder='fake-tester',
          parent_buildername='fake-builder'),
      ctbc_api.properties(
          ctbc_api.properties_assembler_for_ci_tester(
              builder_group='fake-group',
              builder='fake-tester',
          ).with_parent(
              builder_group='fake-group',
              builder='fake-builder',
          ).assemble()),
      api.properties(script_test=True),
  )
