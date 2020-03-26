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
from recipe_engine import post_process
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from RECIPE_MODULES.build import chromium

DEPS = [
    'chromium',
    'chromium_checkout',
    'chromium_swarming',
    'chromium_tests',
    'depot_tools/gclient',
    'isolate',
    'recipe_engine/commit_position',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/step',
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
  api.chromium_swarming.verbose = True

  # Run tests from chromium.swarm buildbot with a relatively high priority
  # so that they take precedence over manually triggered tasks.
  api.chromium_swarming.default_priority = 20

  # Do not care about the OS specific version on Canary.
  api.chromium_swarming.set_default_dimension(
      'os',
      api.chromium_swarming.prefered_os_dimension(
          api.platform.name).split('-', 1)[0])
  if api.platform.is_win:
    # Force os:Windows-10 instead of os:Windows which may trigger on Windows 7.
    api.chromium_swarming.set_default_dimension('os', 'Windows-10')

  api.chromium_swarming.set_default_dimension('pool', 'chromium.tests')
  api.chromium_swarming.add_default_tag('project:chromium')
  api.chromium_swarming.add_default_tag('purpose:staging')
  api.chromium_swarming.default_idempotent = True

  # We are checking out Chromium with swarming_client dep unpinned and pointing
  # to ToT of swarming_client repo, see recipe_modules/gclient/config.py.
  bot_config = api.chromium_tests.create_bot_config_object(
      [chromium.BuilderId.create_for_master(mastername, buildername)])
  api.chromium_swarming.swarming_server = (
      bot_config.swarming_server or 'https://chromium-swarm-dev.appspot.com')

  api.chromium_tests.configure_build(bot_config)
  api.gclient.c.solutions[0].custom_vars['swarming_revision'] = ''
  api.gclient.c.revisions['src/tools/swarming_client'] = 'HEAD'
  update_step = api.chromium_checkout.ensure_checkout(bot_config)

  # Ensure swarming_client version is fresh enough.
  api.chromium_swarming.check_client_version()

  build_config = bot_config.create_build_config(api.chromium_tests, update_step)
  compile_targets = build_config.get_compile_targets(build_config.all_tests())

  # Build all supported tests.
  api.chromium.ensure_goma()
  api.chromium.runhooks()
  raw_result = api.chromium_tests.compile_specific_targets(
      bot_config, update_step, build_config, compile_targets,
      build_config.all_tests())
  if raw_result.status != common_pb.SUCCESS:
    return raw_result

  platform_to_os = {
      'android': 'Android',
      'chromeos': 'ChromeOS',
  }
  if api.chromium.c.TARGET_PLATFORM in platform_to_os:
    api.chromium_swarming.set_default_dimension(
        'os', platform_to_os[api.chromium.c.TARGET_PLATFORM])
    api.chromium_swarming.set_default_dimension('gpu', None)
    api.chromium_swarming.set_default_dimension('cpu', None)

  test_runner = api.chromium_tests.create_test_runner(build_config.all_tests())
  with api.chromium_tests.wrap_chromium_tests(bot_config,
                                              build_config.all_tests()):
    return test_runner()


def GenTests(api):
  yield api.test(
      'android',
      api.properties(
          buildername='android-kitkat-arm-rel-swarming',
          mastername='chromium.dev',
          bot_id='TestSlave',
          buildnumber=123,
          path_config='generic'),
  )

  yield api.test(
      'linux-rel-swarming-staging',
      api.properties(
          buildername='linux-rel-swarming-staging',
          mastername='chromium.dev',
          bot_id='TestSlave',
          buildnumber=123,
          path_config='generic'),
      api.chromium_tests.read_source_side_spec(
          'chromium.dev', {
              'linux-rel-swarming-staging': {
                  'gtest_tests': [{
                      'test': 'browser_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 2,
                      }
                  },],
              },
          }),
      api.override_step_data('find isolated tests',
                             api.json.output({
                                 'browser_tests': 'deadbeef',
                             })),
  )

  # One 'collect' fails due to a missing shard and failing test, should not
  # prevent the second 'collect' from running.
  yield api.test(
      'one_fails',
      api.properties(
          buildername='linux-rel-swarming',
          mastername='chromium.dev',
          bot_id='TestSlave',
          buildnumber=123,
          path_config='generic'),
      api.chromium_tests.read_source_side_spec(
          'chromium.dev', {
              'linux-rel-swarming': {
                  'gtest_tests': [{
                      'test': 'browser_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 2,
                      }
                  },],
              },
          }),
      api.override_step_data('find isolated tests',
                             api.json.output({
                                 'browser_tests': 'deadbeef',
                             })),
      api.override_step_data(
          'browser_tests on Ubuntu',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(
                  passing=False,
                  minimal=True,
                  extra_json={'missing_shards': [1]}),
              failure=True)),
  )

  yield api.test(
      'windows',
      api.properties(
          buildername='win-rel-swarming',
          mastername='chromium.dev',
          bot_id='TestSlave',
          buildnumber=123,
          path_config='generic'),
      api.platform('win', 64),
      api.chromium_tests.read_source_side_spec(
          'chromium.dev', {
              'win-rel-swarming': {
                  'gtest_tests': [{
                      'test': 'browser_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 2,
                      }
                  },],
              },
          }),
      api.override_step_data('find isolated tests',
                             api.json.output({
                                 'browser_tests': 'deadbeef',
                             })),
  )

  yield api.test(
      'compile_failure',
      api.properties(
          buildername='linux-rel-swarming',
          mastername='chromium.dev',
          bot_id='TestSlave',
          buildnumber=123,
          path_config='generic'),
      api.chromium_tests.read_source_side_spec(
          'chromium.dev', {
              'linux-rel-swarming': {
                  'gtest_tests': [{
                      'test': 'browser_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 2,
                      }
                  },],
              },
          }),
      api.step_data('compile', retcode=1),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )
