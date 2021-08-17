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

from recipe_engine import post_process
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb

DEPS = [
    'builder_group',
    'chromium',
    'chromium_checkout',
    'chromium_swarming',
    'chromium_tests',
    'chromium_tests_builder_config',
    'depot_tools/gclient',
    'isolate',
    'recipe_engine/buildbucket',
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


def RunSteps(api):
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
  builder_id, builder_config = (
      api.chromium_tests_builder_config.lookup_builder())
  api.chromium_swarming.swarming_server = (
      builder_config.swarming_server or
      'https://chromium-swarm-dev.appspot.com')

  api.chromium_tests.configure_build(builder_config)
  update_step = api.chromium_checkout.ensure_checkout(builder_config)

  targets_config = (
      api.chromium_tests.create_targets_config(builder_config, update_step))

  # Build all supported tests.
  api.chromium.ensure_goma()
  api.chromium.runhooks()
  raw_result = api.chromium_tests.compile_specific_targets(
      builder_id, builder_config, update_step, targets_config,
      targets_config.compile_targets, targets_config.all_tests)
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

  test_runner = api.chromium_tests.create_test_runner(targets_config.all_tests)
  with api.chromium_tests.wrap_chromium_tests(builder_config,
                                              targets_config.all_tests):
    return test_runner()


def GenTests(api):
  def builder_with_config(buildername, config=None):
    build = api.buildbucket.ci_build_message(
        project='chromium',
        bucket='dev',
        builder=buildername,
        build_number=123,
        git_repo='https://chromium.googlesource.com/chromium/src',
    )
    ret = api.buildbucket.build(build)
    ret += api.builder_group.for_current('chromium.dev')
    if config:
      ret += api.chromium_tests.read_source_side_spec(
          'chromium.dev', {buildername: config})
    return ret

  yield api.test(
      'android',
      builder_with_config('android-lollipop-arm-rel-swarming'),
  )

  yield api.test(
      'linux-rel-swarming-staging',
      builder_with_config('linux-rel-swarming-staging', {
        'gtest_tests': [{
          'test': 'browser_tests',
          'swarming': {
            'can_use_on_swarming_builders': True,
            'shards': 2,
          }
        },],
      }),
  )

  # One 'collect' fails due to a missing shard and failing test, should not
  # prevent the second 'collect' from running.
  yield api.test(
      'one_fails',
      builder_with_config('linux-rel-swarming', {
        'gtest_tests': [{
          'test': 'browser_tests',
          'swarming': {
            'can_use_on_swarming_builders': True,
            'shards': 2,
          }
        },],
      }),
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
      builder_with_config('win-rel-swarming', {
        'gtest_tests': [{
          'test': 'browser_tests',
          'swarming': {
            'can_use_on_swarming_builders': True,
            'shards': 2,
          }
        },],
      }),
      api.platform('win', 64),
  )

  yield api.test(
      'compile_failure',
      builder_with_config('linux-rel-swarming', {
        'gtest_tests': [{
          'test': 'browser_tests',
          'swarming': {
            'can_use_on_swarming_builders': True,
            'shards': 2,
          }
        },],
      }),
      api.step_data('compile', retcode=1),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )
