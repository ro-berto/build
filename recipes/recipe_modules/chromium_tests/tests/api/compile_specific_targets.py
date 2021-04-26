# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine.post_process import Filter

from RECIPE_MODULES.build.chromium_tests import steps
from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
]

BUILDERS = ctbc.BuilderDatabase.create({
    'fake.group': {
        'Test Version':
            ctbc.BuilderSpec.create(
                android_config='main_builder_mb',
                chromium_config='chromium',
                gclient_config='chromium',
                test_results_config='public_server',
                android_version='chrome/Version',
            ),
    },
})


def RunSteps(api):
  tests = []
  if api.properties.get('swarming_gtest'):
    tests.append(
        steps.SwarmingGTestTestSpec.create('base_unittests').get_test())

  _, builder_config = api.chromium_tests_builder_config.lookup_builder()
  api.chromium_tests.configure_build(builder_config)
  update_step, targets_config = (
      api.chromium_tests.prepare_checkout(builder_config))
  return api.chromium_tests.compile_specific_targets(
      builder_config,
      update_step,
      targets_config,
      compile_targets=['base_unittests'],
      tests_including_triggered=tests,
      override_execution_mode=ctbc.COMPILE_AND_TEST)


def GenTests(api):
  yield api.test(
      'linux_tests',
      api.chromium.ci_build(
          builder_group='chromium.linux', builder='Linux Tests'),
      api.properties(swarming_gtest=True),
  )

  yield api.test(
      'linux_tests_reclient',
      api.chromium.ci_build(
          builder_group='chromium.fyi',
          builder='Linux Builder (j-500) (reclient)'),
      api.properties(swarming_gtest=True),
      api.step_data('lookup GN args',
                    api.raw_io.stream_output('use_rbe = true\n')),
      # Check that we do use reclient as the distributed compiler
      api.post_process(post_process.MustRun,
                       'preprocess for reclient.start reproxy via bootstrap'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failure',
      api.chromium.ci_build(
          builder_group='chromium.linux', builder='Linux Tests'),
      api.properties(swarming_gtest=True),
      api.step_data('compile', retcode=1),
  )

  yield api.test(
      'failure_tryserver',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.step_data('compile (with patch)', retcode=1),
  )

  yield api.test(
      'perf_isolate_lookup',
      api.chromium.ci_build(
          builder_group='chromium.perf', builder='linux-builder-perf'),
      api.properties(swarming_gtest=True),
      api.post_process(Filter('pinpoint isolate upload')),
  )

  yield api.test(
      'perf_isolate_lookup_tryserver',
      api.chromium.try_build(
          builder_group='tryserver.chromium.perf',
          builder='Mac Builder Perf',
          change_number=671632,
          patch_set=1),
      api.properties(
          deps_revision_overrides={'src': '12345678' * 5}, swarming_gtest=True),
      api.post_process(Filter('pinpoint isolate upload')),
  )

  yield api.test(
      'android',
      api.chromium.ci_build(
          builder_group='chromium.android', builder='android-cronet-arm-rel'),
  )

  yield api.test(
      'android_version',
      api.chromium_tests_builder_config.ci_build(
          builder_group='fake.group',
          builder='Test Version',
          builder_db=BUILDERS),
      api.chromium.override_version(major=123, minor=1, build=9876, patch=2),
  )
