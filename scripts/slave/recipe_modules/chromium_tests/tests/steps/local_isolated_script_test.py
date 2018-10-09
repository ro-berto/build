# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_tests',
    'isolate',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/step',
    'test_utils',
]

from recipe_engine import post_process


def RunSteps(api):
  test_name = api.properties.get('test_name') or 'base_unittests'

  test = api.chromium_tests.steps.LocalIsolatedScriptTest(
      test_name,
      override_compile_targets=api.properties.get('override_compile_targets'))

  test_repeat_count = api.properties.get('repeat_count')
  if test_repeat_count:
      test.test_options = api.chromium_tests.steps.TestOptions(
          test_filter=api.properties.get('test_filter'),
          repeat_count=test_repeat_count,
          retry_limit=0,
          run_disabled=bool(test_repeat_count)
      )

  try:
    test.pre_run(api, '')
    test.run(api, '')
  finally:
    api.step('details', [])
    api.step.active_result.presentation.logs['details'] = [
        'compile_targets: %r' % test.compile_targets(api),
        'isolate_target: %r' % test.isolate_target,
        'uses_local_devices: %r' % test.uses_local_devices,
        'uses_isolate: %r' % test.uses_isolate,
    ]

    if api.properties.get('log_pass_fail_counts'):
      api.step.active_result.presentation.logs['details'] = [
        'pass_fail_counts: %r' % test.pass_fail_counts(api, '')
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
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          })
  )

  yield (
      api.test('override_compile_targets') +
      api.properties(
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          override_compile_targets=['base_unittests_run'])
  )

  yield (
      api.test('log_pass_fail_counts') +
      api.properties(
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          log_pass_fail_counts=True) +
      api.post_process(verify_log_fields, {'pass_fail_counts': {}}) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('log_pass_fail_counts_invalid_results') +
      api.properties(
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          log_pass_fail_counts=True) +
      api.override_step_data(
        'base_unittests',
        api.test_utils.m.json.output({'interrupted': True}, 255)
        ) +
      api.post_process(verify_log_fields, {'pass_fail_counts': {}}) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('customized_test_options') +
      api.properties(
          swarm_hashes={
            'webkit_layout_tests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          test_filter=['test1', 'test2'],
          repeat_count=20,
          test_name='webkit_layout_tests')
  )
