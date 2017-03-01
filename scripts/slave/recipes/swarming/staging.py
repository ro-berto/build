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
    'configuration': Property(default='Release'),
    'platform': Property(default='linux'),
}


def RunSteps(api, buildername, mastername, configuration, platform):
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

  # We are building simplest Chromium flavor possible.
  chromium_config = 'chromium'
  if platform == 'android':
    chromium_config = 'android'
  api.chromium.set_config(
      chromium_config, BUILD_CONFIG=configuration)

  # We are checking out Chromium with swarming_client dep unpinned and pointing
  # to ToT of swarming_client repo, see recipe_modules/gclient/config.py.
  api.gclient.set_config('chromium')
  if platform == 'android':
    api.gclient.apply_config('android')
  api.gclient.c.solutions[0].custom_vars['swarming_revision'] = ''
  api.gclient.c.revisions['src/tools/swarming_client'] = 'HEAD'

  api.chromium.cleanup_temp()
  # Checkout chromium + deps (including 'master' of swarming_client).
  api.gclient.checkout()

  # Ensure swarming_client version is fresh enough.
  api.swarming.check_client_version()

  # Representative subset of chromium tests to run.
  # TODO(bpastene): Use src-side testing specs instead (if possible.)
  compile_targets = [
      'base_unittests',
      'content_browsertests',
      'content_unittests',
      'net_unittests',
      'unit_tests',
  ]
  isolate_targets = compile_targets
  if platform != 'android':
    # Desktop-only tests.
    additional_targets = [
        'browser_tests',
        'interactive_ui_tests',
    ]
  else:
    # Android GTests need '_apk_run' appended to their compile target, but not
    # isolate target.
    # TODO(bpastene): Remove _apk_run once unit_tests is disambiguated.
    compile_targets = [t + '_apk_run' for t in compile_targets]

    # Android-only instrumentation tests. (They don't have the '_apk_run'
    # difference.)
    additional_targets = [
        'android_webview_test_apk',
        'chrome_public_test_apk',
    ]
  compile_targets.extend(additional_targets)
  isolate_targets.extend(additional_targets)

  # Build all supported tests.
  api.chromium.ensure_goma()
  api.chromium.runhooks()
  api.isolate.clean_isolated_files(api.chromium.output_dir)
  api.chromium.run_mb(
      mastername, buildername,
      use_goma=True, isolated_targets=isolate_targets)
  api.chromium.compile(targets=compile_targets, use_goma_module=True)
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
  if platform == 'android':
    for task in tasks:
      task.dimensions['os'] = 'Android'
      del task.dimensions['cpu']
      del task.dimensions['gpu']
      # TODO(crbug.com/692200): Make android sharding actually work.
      task.hard_timeout = 2 * 60 * 60

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
    api.properties(configuration='Debug') +
    api.override_step_data(
        'dummy_target_1 on Ubuntu',
        api.test_utils.canned_gtest_output(
            passing=False,
            minimal=True,
            extra_json={'missing_shards': [1]}),
    )
  )
  yield (
    api.test('android') +
    api.platform.name('linux') +
    api.properties.scheduled() +
    api.properties(configuration='Release', platform='android') +
    api.override_step_data(
        'isolate tests',
        api.isolate.output_json(targets=[
            'dummy_target_1', 'dummy_target_2', 'chrome_public_test_apk'])
    )
  )
