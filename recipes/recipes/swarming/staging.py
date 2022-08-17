# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Swarming staging recipe: runs tests for HEAD of chromium on Swarming staging
 server instances (*-dev.appspot.com).

Intended to catch bugs in Swarming servers early on, before full roll out.

Waterfall page:
https://luci-milo-dev.appspot.com/p/chromium/g/chromium.dev/console
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
    'recipe_engine/buildbucket',
    'recipe_engine/commit_position',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/step',
    'test_results',
    'test_utils',
]


def RunSteps(api):
  # Configure swarming modules to use staging instances.
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

  builder_id, builder_config = (
      api.chromium_tests_builder_config.lookup_builder())

  api.chromium_tests.configure_build(builder_config)
  update_step = api.chromium_checkout.ensure_checkout(builder_config)

  targets_config = (
      api.chromium_tests.create_targets_config(
          builder_config, update_step.presentation.properties,
          api.chromium_checkout.src_dir))

  # Build all supported tests.
  api.chromium.ensure_goma()
  api.chromium.runhooks()
  raw_result, _ = api.chromium_tests.compile_specific_targets(
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

  # mac-arm-rel-swarming takes long time because there is only 1 tester bot.
  if api.platform.is_mac and api.platform.arch == 'arm':
    api.chromium_swarming.default_expiration = 60 * 60 * 2

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
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', '', custom_os='Ubuntu', failures=['Test.Two']),
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
      'mac-arm',
      builder_with_config('mac-arm-rel-swarming'),
      api.platform('mac', 64),
      api.platform.arch('arm'),
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
