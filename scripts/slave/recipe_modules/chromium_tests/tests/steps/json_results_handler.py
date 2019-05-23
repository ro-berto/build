# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_tests',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/step',
    'test_utils',
    'traceback',
]


def RunSteps(api):
  results_step = api.step('results', [api.json.output()])
  results = results_step.json.output
  test_results = api.test_utils.create_results_from_json(results)

  handler = api.chromium_tests.steps.JSONResultsHandler()

  presentation_step = api.step('presentation_step', [])
  handler.render_results(api, test_results, presentation_step.presentation)

  validated_results = handler.validate_results(api, results)
  api.step('details', [])
  api.step.active_result.presentation.logs['details'] = [
      'valid: %r' % validated_results['valid'],
      'unexpected_failures: %r' % validated_results['failures'],
  ]


def GenTests(api):
  yield (
      api.test('invalid')
  )

  yield (
      api.test('passing') +
      api.step_data(
          'results',
          api.test_utils.canned_isolated_script_output(
              passing=True, is_win=False, swarming=False,
              isolated_script_passing=True,
              use_json_test_format=True))
  )

  yield (
      api.test('failures') +
      api.step_data(
          'results',
          api.test_utils.canned_isolated_script_output(
              passing=False, is_win=False, swarming=False,
              isolated_script_passing=False,
              use_json_test_format=True,
              add_shard_index=True))
  )

  yield (
      api.test('unknown') +
      api.step_data(
          'results',
          api.test_utils.canned_isolated_script_output(
              passing=True, is_win=False, swarming=False,
              isolated_script_passing=True,
              use_json_test_format=True, unknown=True))
  )
