# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
    'test_utils',
]


def RunSteps(api):
  api.chromium.set_config('chromium')

  test = api.chromium_tests.steps.MiniInstallerTest()

  try:
    test.run(api, '')
  finally:
    api.step('details', [])
    api.step.active_result.presentation.logs['details'] = [
        'compile_targets: %r' % test.compile_targets(),
        'uses_local_devices: %r' % test.uses_local_devices,
    ]


def GenTests(api):
  yield api.test('basic')

  example_failure_results = (
  """
      {
        "tests": {
          "__main__": {
            "InstallerTest": {
              "ChromeSystemLevel": {
                "expected": "PASS",
                "actual": "FAIL",
                "is_unexpected": true
              },
              "MigrateMultiStrandedBinariesOnUpdate": {
                "expected": "PASS",
                "actual": "FAIL",
                "is_unexpected": true
              }
            }
          }
        },
        "interrupted": false,
        "path_delimiter": ".",
        "version": 3,
        "seconds_since_epoch": 1537304440.948,
        "num_failures_by_type": {
          "FAIL": 2,
          "PASS": 0
        }
      }
  """
  )

  yield (
      api.test('basic_failure') +
      api.override_step_data(
          'test_installer',
          api.test_utils.test_results(example_failure_results, retcode=1)) +
      api.post_process(post_process.MustRun, 'test_installer') +
      api.post_process(post_process.StepFailure, 'test_installer') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('invalid_results_but_still_valid_json') +
      api.override_step_data(
          'test_installer',
          api.test_utils.test_results('{}', retcode=1)) +
      api.post_process(post_process.MustRun, 'test_installer') +
      api.post_process(post_process.StepException, 'test_installer') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('invalid_json') +
      api.override_step_data(
          'test_installer',
          api.test_utils.test_results('{', retcode=1)) +
      api.post_process(post_process.MustRun, 'test_installer') +
      api.post_process(post_process.StepException, 'test_installer') +
      api.post_process(post_process.DropExpectation)
  )
