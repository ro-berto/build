# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import Filter

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

  mastername = api.properties['mastername']
  if api.tryserver.is_tryserver and mastername in api.chromium_tests.trybots:
    bot_config = api.chromium_tests.trybots[
        mastername]['builders'][api.properties['buildername']]
    bot_config_object = api.chromium_tests.create_generalized_bot_config_object(
        bot_config['bot_ids'])
  else:
    bot_config_object = api.chromium_tests.create_bot_config_object(
        mastername, api.properties['buildername'])
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
          buildername='Linux Builder Perf',
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
      api.test('update_clang') +
      api.platform.name('win') +
      api.properties.generic(
          mastername='chromium.clang',
          buildername='CrWinClang64(dbg)')
  )

  yield (
      api.test('android') +
      api.properties.generic(
          mastername='chromium.android',
          buildername='Android Cronet Builder')
  )
