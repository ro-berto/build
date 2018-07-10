# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_tests',
    'depot_tools/tryserver',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/step',
    'test_results',
    'test_utils',
]

from recipe_engine import post_process


def RunSteps(api):
  api.chromium.set_config('chromium')
  api.test_results.set_config('public_server')

  tests = [
      api.chromium_tests.steps.MockTest(
          name=api.properties.get('test_name', 'MockTest'),
          abort_on_failure=api.properties.get('abort_on_failure', False)),
      api.chromium_tests.steps.MockTest(name='test2')
  ]

  failed_tests = api.test_utils.run_tests(
      api.chromium_tests.m, tests, '')
  if failed_tests:
    raise api.step.StepFailure('failed: %s' % ' '.join(t.name for t in failed_tests))


def GenTests(api):
  failure_code = api.chromium_tests.steps.MockTest.ExitCodes.FAILURE
  infra_code = api.chromium_tests.steps.MockTest.ExitCodes.INFRA_FAILURE

  yield (
      api.test('success') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          bot_id='test_bot_id',
          buildnumber=123,
          test_name='base_unittests') +
      api.post_process(post_process.MustRun, 'test2') +
      api.post_process(post_process.StatusCodeIn, 0) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('failure') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          bot_id='test_bot_id',
          buildnumber=123,
          test_name='base_unittests') +
      api.override_step_data('base_unittests', retcode=failure_code) +
      api.post_process(post_process.MustRun, 'test2') +
      api.post_process(post_process.StatusCodeIn, 1) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('failure_abort') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          bot_id='test_bot_id',
          buildnumber=123,
          test_name='base_unittests',
          abort_on_failure=True) +
      api.override_step_data('base_unittests', retcode=failure_code) +
      api.post_process(post_process.DoesNotRun, 'test2') +
      api.post_process(post_process.StatusCodeIn, 1) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('infra_failure') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          bot_id='test_bot_id',
          buildnumber=123,
          test_name='base_unittests') +
      api.override_step_data('base_unittests', retcode=infra_code) +
      api.post_process(post_process.DoesNotRun, 'test2') +
      api.post_process(post_process.StatusCodeIn, 2) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('pre_run_failure') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          bot_id='test_bot_id',
          buildnumber=123,
          test_name='base_unittests') +
      api.override_step_data(
          'test_pre_run.pre_run base_unittests',
          retcode=failure_code) +
      api.post_process(post_process.MustRun, 'base_unittests') +
      api.post_process(post_process.MustRun, 'test2') +
      api.post_process(post_process.StatusCodeIn, 1) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('pre_run_infra_failure') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          bot_id='test_bot_id',
          buildnumber=123,
          test_name='base_unittests') +
      api.override_step_data(
          'test_pre_run.pre_run base_unittests',
          retcode=infra_code) +
      api.post_process(post_process.DoesNotRun, 'base_unittests') +
      api.post_process(post_process.StatusCodeIn, 2) +
      api.post_process(post_process.DropExpectation)
  )
