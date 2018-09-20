# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_tests',
    'commit_position',
    'depot_tools/bot_update',
    'isolate',
    'recipe_engine/json',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
    'swarming',
    'test_results',
    'test_utils',
]

from recipe_engine import post_process


def RunSteps(api):
  api.chromium.set_config(
      'chromium',
      TARGET_PLATFORM=api.properties.get('target_platform', 'linux'))

  test = api.chromium_tests.steps.SwarmingGTestTest(
      'base_unittests',
      override_isolate_target=api.properties.get('override_isolate_target'),
      override_compile_targets=api.properties.get('override_compile_targets'))

  test_options = api.chromium_tests.steps.TestOptions()
  test.test_options = test_options

  try:
    test.pre_run(api, '')
    test.run(api, '')
  finally:
    api.step('details', [])
    api.step.active_result.presentation.logs['details'] = [
      'compile_targets: %r' % test.compile_targets(api),
      'uses_local_devices: %r' % test.uses_local_devices,
      'uses_isolate: %r' % test.uses_isolate,
      'pass_fail_counts: %r' % test.pass_fail_counts(''),
    ]



def GenTests(api):

  def verify_log_fields(check, step_odict, expected_fields):
    """Verifies fields in details log are with expected values."""
    step = step_odict['details']
    followup_annotations = step['~followup_annotations']
    for key, value in expected_fields.iteritems():
      expected_log = '@@@STEP_LOG_LINE@details@%s: %r@@@' % (key, value)
      check(expected_log in followup_annotations)
    return step_odict

  yield (
      api.test('basic') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests',
          api.swarming.canned_summary_output(failure=False) +
          api.test_utils.canned_gtest_output(passing=True))
  )

  yield (
      api.test('android') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          target_platform='android',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          })
  )

  yield (
      api.test('overrides') +
      api.properties(
          override_isolate_target='base_unittests_run',
          override_compile_targets=['base_unittests_run'],
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          })
  )

  yield (
      api.test('no_result_json') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests',
          api.swarming.canned_summary_output(failure=True),
          retcode=1)
  )

  yield (
      api.test('invalid_test_result') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'base_unittests',
          api.swarming.canned_summary_output() +
          api.test_utils.gtest_results(None, 255)) +
      api.post_process(verify_log_fields, {'pass_fail_counts': {}}) +
      api.post_process(post_process.DropExpectation)
  )
