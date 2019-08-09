# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import (Filter,
      DropExpectation, ResultReason, StatusFailure)
from PB.recipe_engine import result as result_pb2
import textwrap

DEPS = [
    'chromium',
    'chromium_tests',
    'depot_tools/tryserver',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/json',
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
    tests.append(api.chromium_tests.steps.SwarmingGTestTest('base_unittests'))

  mastername = api.properties['mastername']
  buildername = api.properties['buildername']
  if api.tryserver.is_tryserver and mastername in api.chromium_tests.trybots:
    bot_config = api.chromium_tests.trybots[mastername]['builders'][buildername]
    bot_config_object = api.chromium_tests.create_bot_config_object(
        bot_config['bot_ids'])
  else:
    builders = BUILDERS if 'fake.master' in mastername else None
    bot_config_object = api.chromium_tests.create_bot_config_object(
        [api.chromium_tests.create_bot_id(mastername, buildername)],
        builders=builders)
  api.chromium_tests.configure_build(bot_config_object)
  update_step, bot_db = api.chromium_tests.prepare_checkout(bot_config_object)
  return api.chromium_tests.compile_specific_targets(
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
      api.step_data('compile', retcode=1)
  )

  yield (
      api.test('failure_tryserver') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel') +
      api.step_data('compile (with patch)', retcode=1)
  )

  yield (
      api.test('failure_mb_gen') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests',
          swarming_gtest=True) +
      api.override_step_data('generate_build_files',
        api.json.output({
          'output': 'ERROR at line 5: missing )',
          'retcode': 1
        }, name="failure_summary"), retcode=1) +
      api.post_process(StatusFailure) +
      api.post_process(ResultReason, textwrap.dedent('''
          ```
          ERROR at line 5: missing )
          ```
      ''').strip()) +
      api.post_process(DropExpectation)
  )

  yield (
      api.test('perf_isolate_lookup') +
      api.properties.generic(
          mastername='chromium.perf',
          buildername='linux-builder-perf',
          swarming_gtest=True) +
          api.post_process(Filter('pinpoint isolate upload'))
  )

  yield (
      api.test('perf_isolate_lookup_tryserver') +
      api.properties.tryserver(
          mastername='tryserver.chromium.perf',
          buildername='Mac Builder Perf',
          deps_revision_overrides={'src': '1234567890abcdef'},
          patch_gerrit_url='https://chromium-review.googlesource.com',
          patch_issue=671632,
          patch_project='chromium/src',
          patch_ref='refs/changes/32/671632/1',
          patch_repository_url='https://chromium.googlesource.com/chromium/src',
          patch_set=1,
          patch_storage='gerrit',
          swarming_gtest=True) +
          api.post_process(Filter('pinpoint isolate upload'))
  )

  yield (
      api.test('android') +
      api.properties.generic(
          mastername='chromium.android',
          buildername='android-cronet-arm-rel')
  )

  yield (
      api.test('android_version') +
      api.properties.generic(
          mastername='fake.master',
          buildername='Test Version') +
      api.chromium.override_version(
          major=123, minor=1, build=9876, patch=2)
  )
