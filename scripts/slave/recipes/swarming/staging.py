# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Swarming staging recipe: runs tests for HEAD of chromium using HEAD of
swarming_client toolset on Swarming staging server instances
(*-dev.appspot.com).

Intended to catch bugs in swarming_client and Swarming servers early on, before
full roll out.

Waterfall page: https://build.chromium.org/p/chromium.swarm/waterfall
"""

from recipe_engine.recipe_api import Property

DEPS = [
  'depot_tools/bot_update',
  'chromium',
  'chromium_tests',
  'commit_position',
  'file',
  'depot_tools/gclient',
  'isolate',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/step',
  'swarming',
  'swarming_client',
  'test_results',
  'test_utils',
]


PROPERTIES = {
    'buildername': Property(default=''),
    'mastername': Property(default=''),
}


def RunSteps(api, buildername, mastername):
  # Configure isolate & swarming modules to use staging instances.
  api.isolate.isolate_server = 'https://isolateserver-dev.appspot.com'
  api.swarming.swarming_server = 'https://chromium-swarm-dev.appspot.com'
  api.swarming.verbose = True

  # Run tests from chromium.swarm buildbot with a relatively high priority
  # so that they take precedence over manually triggered tasks.
  api.swarming.default_priority = 20

  # Do not care about the OS specific version on Canary.
  api.swarming.set_default_dimension(
      'os',
      api.swarming.prefered_os_dimension(api.platform.name).split('-', 1)[0])
  api.swarming.set_default_dimension('pool', 'Chrome')
  api.swarming.add_default_tag('project:chromium')
  api.swarming.add_default_tag('purpose:staging')
  api.swarming.default_idempotent = True

  # We are checking out Chromium with swarming_client dep unpinned and pointing
  # to ToT of swarming_client repo, see recipe_modules/gclient/config.py.
  bot_config = api.chromium_tests.create_bot_config_object(
      mastername, buildername)
  api.chromium_tests.configure_build(bot_config)
  api.gclient.c.solutions[0].custom_vars['swarming_revision'] = ''
  api.gclient.c.revisions['src/tools/swarming_client'] = 'HEAD'
  update_step = api.bot_update.ensure_checkout()

  # Ensure swarming_client version is fresh enough.
  api.swarming.check_client_version()

  bot_db = api.chromium_tests.create_bot_db_object()
  bot_config.initialize_bot_db(api.chromium_tests, bot_db, update_step)
  _, tests = api.chromium_tests.get_tests(bot_config, bot_db)
  compile_targets = api.chromium_tests.get_compile_targets(
      bot_config, bot_db, tests)

  # Build all supported tests.
  api.chromium.ensure_goma()
  api.chromium.runhooks()
  api.isolate.clean_isolated_files(api.chromium.output_dir)
  api.chromium_tests.compile_specific_targets(
      bot_config, update_step, bot_db, compile_targets, tests)
  api.isolate.remove_build_metadata()

  # Will search for *.isolated.gen.json files in the build directory and isolate
  # corresponding targets.
  api.isolate.isolate_tests(
      api.chromium.output_dir,
      verbose=True,
      env={'SWARMING_PROFILE': '1'})

  # Make swarming tasks that run isolated tests.
  tasks = [
    api.swarming.gtest_task(
        test,
        isolated_hash,
        shards=2,
        test_launcher_summary_output=api.test_utils.gtest_results(
            add_json_log=False))
    for test, isolated_hash in sorted(api.isolate.isolated_tests.iteritems())
  ]

  for task in tasks:
    api.swarming.trigger_task(task)

  # And wait for ALL them to finish.
  with api.step.defer_results():
    for task in tasks:
      api.swarming.collect_task(task)


def GenTests(api):
  # One 'collect' fails due to a missing shard and failing test, should not
  # prevent the second 'collect' from running.
  yield (
    api.test('one_fails') +
    api.platform.name('linux') +
    api.properties.scheduled() +
    api.properties(
        buildername='Linux Swarm',
        mastername='chromium.swarm') +
    api.override_step_data(
        'dummy_target_1 on Ubuntu',
        api.test_utils.canned_gtest_output(
            passing=False,
            minimal=True,
            extra_json={'missing_shards': [1]}),
    )
  )
