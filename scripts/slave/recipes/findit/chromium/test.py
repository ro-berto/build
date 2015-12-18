# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from recipe_engine.config import Dict
from recipe_engine.recipe_api import Property


DEPS = [
  'adb',
  'bot_update',
  'chromium',
  'chromium_tests',
  'commit_position',
  'findit',
  'gclient',
  'isolate',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',
  'swarming',
  'test_results',
  'test_utils',
]


PROPERTIES = {
    'target_mastername': Property(
        kind=str, help='The target master to match compile config to.'),
    'target_testername': Property(
        kind=str,
        help='The target tester to match test config to. If the tests are run '
             'on a builder, just treat the builder as a tester.'),
    'good_revision': Property(
        kind=str, help='The last known good revision.'),
    'bad_revision': Property(
        kind=str, help='The first known good revision.'),
    'requested_tests': Property(
        kind=Dict(value_type=list), param_name='tests',
        help='The failed tests, the test name should be full name, e.g.: {'
             '  "browser_tests on Windows-XP-SP3": ['
             '    "suite.test1", "suite.test2"'
             '  ]'
             '}'),
}


class TestResult(object):
  SKIPPED = 'skipped'  # A commit doesn't impact the test.
  PASSED = 'passed'  # The compile or test passed.
  FAILED = 'failed'  # The compile or test failed.


def _compile_and_test_at_revision(api, target_mastername, target_buildername,
                                  target_testername, revision, requested_tests):
  results = {}
  with api.step.nest('test %s' % str(revision)):
    # Checkout code at the given revision to recompile.
    bot_update_step, master_dict, _ = \
        api.chromium_tests.prepare_checkout(
            target_mastername,
            target_buildername,
            root_solution_revision=revision)

    # Figure out which test steps to run.
    all_tests = api.chromium_tests.tests_for_builder(
        target_mastername,
        target_testername,  # If not tester, this is same as target_buildername.
        bot_update_step,
        master_dict,
        override_bot_type='builder_tester')

    tests_to_run = [test for test in all_tests if test.name in requested_tests]

    # Figure out which targets to compile.
    compile_targets = []
    for test in tests_to_run:
      compile_targets.extend(test.compile_targets(api))
    compile_targets = sorted(set(compile_targets))

    if compile_targets:
      api.chromium_tests.compile_specific_targets(
          target_mastername,
          target_buildername,
          bot_update_step,
          master_dict,
          compile_targets,
          tests_including_triggered=tests_to_run,
          mb_mastername=target_mastername,
          mb_buildername=target_buildername,
          override_bot_type='builder_tester')

    # Run the tests.
    with api.chromium_tests.wrap_chromium_tests(
        target_mastername, tests_to_run):
      failed_tests = api.test_utils.run_tests(
          api, tests_to_run, suffix=revision, test_filters=requested_tests)

    # Process failed tests.
    for failed_test in failed_tests:
      valid = failed_test.has_valid_results(api, suffix=revision)
      results[failed_test.name] = {
          'status': TestResult.FAILED,
          'valid': valid,
      }
      if valid:
        results[failed_test.name]['failures'] = list(
            failed_test.failures(api, suffix=revision))

    # Process passed tests.
    for test in tests_to_run:
      if test not in failed_tests:
        results[test.name] = {
            'status': TestResult.PASSED,
            'valid': True,
        }

    # Process skipped tests.
    for test_name in requested_tests.keys():
      if test_name not in results:
        results[test_name] = {
            'status': TestResult.SKIPPED,
            'valid': True,
        }

    return results


def RunSteps(api, target_mastername, target_testername,
             good_revision, bad_revision, requested_tests):
  assert requested_tests, 'No failed tests were specified.'

  # Figure out which builder configuration we should match for compile config.
  # Sometimes, the builder itself runs the tests and there is no tester. In
  # such cases, just treat the builder as a "tester". Thus, we default to
  # the target tester.
  tester_config = api.chromium_tests.builders.get(
      target_mastername).get('builders', {}).get(target_testername)
  target_buildername = (tester_config.get('parent_buildername') or
                        target_testername)

  # Configure to match the compile config on the builder.
  api.chromium_tests.configure_build(
      target_mastername, target_buildername, override_bot_type='builder_tester')

  # Configure to match the test config on the tester, as builders don't have the
  # settings for swarming tests.
  if target_buildername != target_testername:
    for key, value in tester_config.get('swarming_dimensions', {}).iteritems():
      api.swarming.set_default_dimension(key, value)
  # TODO(stgao): Fix the issue that precommit=False adds the tag 'purpose:CI'.
  api.chromium_tests.configure_swarming('chromium', precommit=False)

  # Sync to bad revision, and retrieve revisions in the regression range.
  api.chromium_tests.prepare_checkout(
      target_mastername, target_buildername,
      root_solution_revision=bad_revision)
  revisions_to_check = api.findit.revisions_between(good_revision, bad_revision)

  results = {}

  try:
    # We compile & run tests from the first revision to the last revision in the
    # regression range serially instead of a typical bisecting, because jumping
    # between new and old revisions might affect Goma capacity and build cycle
    # times. Thus we plan to go with this simple serial approach first so that
    # compile would be fast due to incremental compile.
    # If this won't work out, we will figure out a better solution for speed of
    # both compile and test.
    for current_revision in revisions_to_check:
      results[current_revision] = _compile_and_test_at_revision(
          api, target_mastername, target_buildername, target_testername,
          current_revision, requested_tests)
      # TODO(http://crbug.com/566975): check whether culprits for all failed
      # tests are found and stop running tests at later revisions if so.
  finally:
    # Report the result.
    step_result = api.python.succeeding_step(
        'report', [json.dumps(results, indent=2)], as_log='result')

    # Set the result as a build property too, so that it will be reported back
    # to Buildbucket and Findit will pull from there instead of buildbot master.
    step_result.presentation.properties['result'] = results

  return results


def GenTests(api):
  def props(tests):
    properties = {
        'mastername': 'tryserver.chromium.win',
        'buildername': 'win_chromium_variable',
        'slavename': 'build1-a1',
        'buildnumber': 1,
        'target_mastername': 'chromium.win',
        'target_testername': 'Vista Tests (1)',
        'good_revision': 'r0',
        'bad_revision': 'r1',
        'tests': tests,
    }
    return api.properties(**properties)

  def simulated_gtest_output(failed_test_names=(), passed_test_names=()):
    cur_iteration_data = {}
    for test_name in failed_test_names:
      cur_iteration_data[test_name] = [{
          'elapsed_time_ms': 0,
          'output_snippet': '',
          'status': 'FAILURE',
      }]
    for test_name in passed_test_names:
      cur_iteration_data[test_name] = [{
          'elapsed_time_ms': 0,
          'output_snippet': '',
          'status': 'SUCCESS',
      }]

    canned_jsonish = {
      'per_iteration_data': [cur_iteration_data]
    }

    return api.test_utils.raw_gtest_output(
        canned_jsonish, 1 if failed_test_names else 0)

  yield (
      api.test('nonexistent_test_step_skipped') +
      props({'newly_added_tests': ['Test.One', 'Test.Two', 'Test.Three']}) +
      api.override_step_data('test r1.read test spec', api.json.output({
          'Vista Tests (1)': {
              'gtest_tests': [
                  {
                    'test': 'gl_tests',
                    'swarming': {'can_use_on_swarming_builders': True},
                  },
              ],
          },
      }))
  )

  yield (
      api.test('all_test_failed') +
      props({'gl_tests': ['Test.One', 'Test.Two', 'Test.Three']}) +
      api.override_step_data('test r1.read test spec', api.json.output({
          'Vista Tests (1)': {
              'gtest_tests': [
                  {
                    'test': 'gl_tests',
                    'swarming': {'can_use_on_swarming_builders': True},
                  },
              ],
          },
      })) +
      api.override_step_data(
          'test r1.gl_tests (r1) on Windows-Vista-SP2',
          simulated_gtest_output(
              failed_test_names=['Test.One', 'Test.Two', 'Test.Three'])
      )
  )
  yield (
      api.test('all_test_passed') +
      props({'gl_tests': ['Test.One', 'Test.Two', 'Test.Three']}) +
      api.override_step_data('test r1.read test spec', api.json.output({
          'Vista Tests (1)': {
              'gtest_tests': [
                  {
                    'test': 'gl_tests',
                    'swarming': {'can_use_on_swarming_builders': True},
                  },
              ],
          },
      })) +
      api.override_step_data(
          'test r1.gl_tests (r1) on Windows-Vista-SP2',
          simulated_gtest_output(
              passed_test_names=['Test.One', 'Test.Two', 'Test.Three'])
      )
  )

  yield (
      api.test('only_one_test_passed') +
      props({'gl_tests': ['Test.One', 'Test.Two', 'Test.Three']}) +
      api.override_step_data('test r1.read test spec', api.json.output({
          'Vista Tests (1)': {
              'gtest_tests': [
                  {
                    'test': 'gl_tests',
                    'swarming': {'can_use_on_swarming_builders': True},
                  },
              ],
          },
      })) +
      api.override_step_data(
          'test r1.gl_tests (r1) on Windows-Vista-SP2',
          simulated_gtest_output(
              failed_test_names=['Test.One', 'Test.Two'],
              passed_test_names=['Test.Three'])
      )
  )

  yield (
      api.test('compile_skipped') +
      props({'checkperms': []}) +
      api.override_step_data('test r1.read test spec', api.json.output({
          'Vista Tests (1)': {
              'scripts': [
                  {
                      'name': 'checkperms',
                      'script': 'checkperms.py'
                  },
              ]
          },
      }))
  )

  yield (
      api.test('none_swarming_tests') +
      props({'gl_tests': ['Test.One', 'Test.Two', 'Test.Three']}) +
      api.override_step_data('test r1.read test spec', api.json.output({
          'Vista Tests (1)': {
              'gtest_tests': [
                  {
                    'test': 'gl_tests',
                    'swarming': {'can_use_on_swarming_builders': False},
                  },
              ],
          },
      })) +
      api.override_step_data(
          'test r1.gl_tests (r1)',
          simulated_gtest_output(
              failed_test_names=['Test.One', 'Test.Two'],
              passed_test_names=['Test.Three'])
      )
  )
