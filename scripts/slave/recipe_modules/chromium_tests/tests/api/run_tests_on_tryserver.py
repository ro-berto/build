# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_tests',
    'recipe_engine/properties',
    'swarming',
    'test_utils',
]


def RunSteps(api):
  bot_config = api.chromium_tests.trybots[
      api.properties['mastername']]['builders'][api.properties['buildername']]
  bot_config_object = api.chromium_tests.create_generalized_bot_config_object(
      bot_config['bot_ids'])
  api.chromium_tests.configure_build(bot_config_object)
  update_step, _bot_db = api.chromium_tests.prepare_checkout(bot_config_object)
  api.chromium_tests._run_tests_on_tryserver(
      bot_config_object,
      tests=[api.chromium_tests.steps.SwarmingGTestTest('base_unittests')],
      bot_update_step=update_step,
      affected_files=api.properties.get('affected_files', []),
      disable_deapply_patch=api.properties.get('disable_deapply_patch'))


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(False))
  )

  yield (
      api.test('disable_deapply_patch_recipes') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng',
          disable_deapply_patch=True,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(False))
  )

  yield (
      api.test('disable_deapply_patch_affected_files') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng',
          affected_files=['testing/buildbot/chromium.linux.json'],
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(False))
  )

  yield (
      api.test('nonzero_exit_code_no_gtest_output') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng',
          affected_files=['testing/buildbot/chromium.linux.json'],
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.swarming.canned_summary_output(failure=True) +
          api.test_utils.raw_gtest_output({'per_iteration_data': []}, 1))
  )
