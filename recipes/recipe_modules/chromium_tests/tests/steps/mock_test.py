# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium_tests',
  'recipe_engine/properties',
  'recipe_engine/step',
]

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import steps


def RunSteps(api):
  test_spec = steps.MockTestSpec.create(
      name=api.properties.get('test_name', 'MockTest'),
      abort_on_failure=api.properties.get('abort_on_failure', False))
  test = test_spec.get_test(api.chromium_tests)

  test.pre_run('')

  try:
    test.run('')
  except api.step.InfraFailure:
    api.step.empty('infra failure in %s' % test.name)
  except api.step.StepFailure:
    if test.abort_on_failure:
      api.step.empty('fatal step failure in %s' % test.name)
    else:
      api.step.empty('step failure in %s' % test.name)


def GenTests(api):
  failure_code = steps.MockTest.ExitCodes.FAILURE
  infra_code = steps.MockTest.ExitCodes.INFRA_FAILURE

  yield api.test('basic')

  yield api.test(
      'failure',
      api.properties(test_name='base_unittests'),
      api.chromium_tests.override_step_data(
          'base_unittests', retcode=failure_code),
      api.post_process(post_process.MustRun, 'step failure in base_unittests'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failure_abort',
      api.properties(abort_on_failure=True, test_name='base_unittests'),
      api.chromium_tests.override_step_data(
          'base_unittests', retcode=failure_code),
      api.post_process(post_process.MustRun,
                       'fatal step failure in base_unittests'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'infra_failure',
      api.properties(test_name='base_unittests'),
      api.chromium_tests.override_step_data(
          'base_unittests', retcode=infra_code),
      api.post_process(post_process.MustRun, 'infra failure in base_unittests'),
      api.post_process(post_process.DropExpectation),
  )
