# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine.post_process import Filter

from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec, steps

DEPS = [
    'chromium',
    'chromium_tests',
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
]

BUILDERS = bot_db.BotDatabase.create({
    'fake.group': {
        'Test Version':
            bot_spec.BotSpec.create(
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

  builder_id = api.chromium.get_builder_id()
  if api.tryserver.is_tryserver and builder_id in api.chromium_tests.trybots:
    try_spec = api.chromium_tests.trybots[builder_id]
    bot_config = api.chromium_tests.create_bot_config_object(try_spec.mirrors)
  else:
    builders = BUILDERS if 'fake.group' in builder_id.group else None
    bot_config = api.chromium_tests.create_bot_config_object(
        [api.chromium.get_builder_id()], builders=builders)
  api.chromium_tests.configure_build(bot_config)
  update_step, build_config = api.chromium_tests.prepare_checkout(bot_config)
  return api.chromium_tests.compile_specific_targets(
      bot_config,
      update_step,
      build_config,
      compile_targets=['base_unittests'],
      tests_including_triggered=tests,
      override_execution_mode=bot_spec.COMPILE_AND_TEST)


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
          builder_group='chromium.fyi', builder='Linux Builder (reclient)'),
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
      api.chromium.ci_build(builder_group='fake.group', builder='Test Version'),
      api.chromium.override_version(major=123, minor=1, build=9876, patch=2),
  )
