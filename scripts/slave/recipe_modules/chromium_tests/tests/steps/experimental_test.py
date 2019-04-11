# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium_tests',
  'depot_tools/tryserver',
  'recipe_engine/buildbucket',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
]

from recipe_engine import post_process


def RunSteps(api):

  inner_test = api.chromium_tests.steps.MockTest(
      'inner_test',
      abort_on_failure=api.properties.get('abort_on_failure', False),
      has_valid_results=api.properties.get('has_valid_results', True),
      failures=api.properties.get('failures'), api=api)
  experimental_test = api.chromium_tests.steps.ExperimentalTest(
      inner_test,
      experiment_percentage=api.properties['experiment_percentage'],
      api=api)

  api.python.succeeding_step(
      'Configured experimental test %s' % experimental_test.name, '')

  suffix = api.properties.get('suffix', '')

  experimental_test.pre_run(api.chromium_tests.m, suffix)
  experimental_test.run(api.chromium_tests.m, suffix)

  assert experimental_test.has_valid_results('')
  assert not experimental_test.failures(api.chromium_tests.m, '')
  assert not experimental_test.deterministic_failures(api.chromium_tests.m, '')
  assert not experimental_test.abort_on_failure
  assert isinstance(experimental_test.pass_fail_counts(
      api.chromium_tests.m, ''), dict)


def GenTests(api):

  yield (
      api.test('experiment_on') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber='123',
          patch_issue='456',
          experiment_percentage='100') +
      api.post_process(post_process.MustRun,
                       'pre_run inner_test (experimental)') +
      api.post_process(post_process.MustRun, 'inner_test (experimental)') +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation))

  yield (
      api.test('experiment_off') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber='123',
          patch_issue='456',
          experiment_percentage='0') +
      api.post_process(post_process.DoesNotRun,
                       'pre_run inner_test (experimental)') +
      api.post_process(post_process.DoesNotRun, 'inner_test (experimental)') +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation))

  yield (
      api.test('experiment_on_invalid_results') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber='123',
          patch_issue='456',
          experiment_percentage='100',
          has_valid_results=False) +
      api.post_process(post_process.MustRun,
                       'has_valid_results inner_test (experimental)') +
      api.post_process(post_process.DoesNotRun,
                       'failures inner_test (experimental)') +
      api.post_process(post_process.DropExpectation))

  yield (
      api.test('experiment_off_invalid_results') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber='123',
          patch_issue='456',
          experiment_percentage='0',
          has_valid_results=False) +
      api.post_process(post_process.DropExpectation))

  yield (
      api.test('experiment_on_valid_failures') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber='123',
          patch_issue='456',
          experiment_percentage='100',
          failures=['foo']) +
      api.post_process(post_process.DropExpectation))

  yield (
      api.test('experiment_off_valid_failures') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber='123',
          patch_issue='456',
          experiment_percentage='0',
          failures=['foo']) +
      api.post_process(post_process.DropExpectation))

  yield (
      api.test('failure_in_pre_run') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber='123',
          patch_issue='456',
          experiment_percentage='100') +
      api.override_step_data('pre_run inner_test (experimental)', retcode=1) +
      api.post_process(post_process.MustRun,
                       'pre_run inner_test (experimental)') +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation))

  yield (
      api.test('failure_in_run') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber='123',
          patch_issue='456',
          experiment_percentage='100') +
      api.override_step_data('inner_test (experimental)', retcode=1) +
      api.post_process(post_process.MustRun, 'inner_test (experimental)') +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation))

  yield (
      api.test('abort_on_failure') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber='123',
          patch_issue='456',
          experiment_percentage='100',
          failures=['foo'],
          abort_on_failure=True) +
      api.post_process(post_process.MustRun, 'inner_test (experimental)') +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation))

  yield (
      api.test('with_patch') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber='123',
          patch_issue='456',
          experiment_percentage='100',
          suffix='with patch') +
      api.post_process(post_process.MustRun,
                       'pre_run inner_test (with patch, experimental)') +
      api.post_process(post_process.MustRun,
                       'inner_test (with patch, experimental)') +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation))
