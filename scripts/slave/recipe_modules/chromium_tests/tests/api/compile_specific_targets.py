# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import Filter

from RECIPE_MODULES.build.chromium_tests import steps

DEPS = [
    'chromium',
    'chromium_tests',
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
    'recipe_engine/properties',
]

BASIC_CONFIG = {
  'android_config': 'main_builder_mb',
  'chromium_config': 'chromium',
  'gclient_config': 'chromium',
  'test_results_config': 'public_server',
}

BUILDERS = {
  'fake.master': {
    'builders': {
      'Test Version': dict(BASIC_CONFIG, **{
        'android_version': 'chrome/Version',
      }),
    },
  },
}

def RunSteps(api):
  tests = []
  if api.properties.get('swarming_gtest'):
    tests.append(steps.SwarmingGTestTest('base_unittests'))

  mastername = api.properties['mastername']
  buildername = api.buildbucket.builder_name
  if api.tryserver.is_tryserver and mastername in api.chromium_tests.trybots:
    bot_config = api.chromium_tests.trybots[mastername]['builders'][buildername]
    bot_config_object = api.chromium_tests.create_bot_config_object(
        bot_config['bot_ids'])
  else:
    builders = BUILDERS if 'fake.master' in mastername else None
    bot_config_object = api.chromium_tests.create_bot_config_object(
        [api.chromium.get_builder_id()], builders=builders)
  api.chromium_tests.configure_build(bot_config_object)
  update_step, build_config = api.chromium_tests.prepare_checkout(
      bot_config_object)
  return api.chromium_tests.compile_specific_targets(
      bot_config_object,
      update_step,
      build_config,
      compile_targets=['base_unittests'],
      tests_including_triggered=tests,
      override_bot_type='builder_tester')


def GenTests(api):
  yield api.test(
      'linux_tests',
      api.chromium.ci_build(mastername='chromium.linux', builder='Linux Tests'),
      api.properties(swarming_gtest=True),
  )

  yield api.test(
      'failure',
      api.chromium.ci_build(mastername='chromium.linux', builder='Linux Tests'),
      api.properties(swarming_gtest=True),
      api.step_data('compile', retcode=1),
  )

  yield api.test(
      'failure_tryserver',
      api.chromium.try_build(
          mastername='tryserver.chromium.linux', builder='linux-rel'),
      api.step_data('compile (with patch)', retcode=1),
  )

  yield api.test(
      'perf_isolate_lookup',
      api.chromium.ci_build(
          mastername='chromium.perf', builder='linux-builder-perf'),
      api.properties(swarming_gtest=True),
      api.post_process(Filter('pinpoint isolate upload')),
  )

  yield api.test(
      'perf_isolate_lookup_tryserver',
      api.chromium.try_build(
          mastername='tryserver.chromium.perf',
          builder='Mac Builder Perf',
          change_number=671632,
          patch_set=1),
      api.properties(
          deps_revision_overrides={'src': '1234567890abcdef'},
          swarming_gtest=True),
      api.post_process(Filter('pinpoint isolate upload')),
  )

  yield api.test(
      'android',
      api.chromium.ci_build(
          mastername='chromium.android', builder='android-cronet-arm-rel'),
  )

  yield api.test(
      'android_version',
      api.chromium.ci_build(mastername='fake.master', builder='Test Version'),
      api.chromium.override_version(major=123, minor=1, build=9876, patch=2),
  )
