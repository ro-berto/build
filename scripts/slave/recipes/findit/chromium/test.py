# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from collections import defaultdict
import json

from recipe_engine.config import Dict
from recipe_engine.config import List
from recipe_engine.config import Single
from recipe_engine.recipe_api import Property


DEPS = [
    'adb',
    'buildbucket',
    'depot_tools/bot_update',
    'chromium',
    'chromium_android',
    'chromium_swarming',
    'chromium_tests',
    'commit_position',
    'filter',
    'findit',
    'depot_tools/gclient',
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
    'tests': Property(
        kind=Dict(value_type=list),
        default={},
        help='The failed tests, the test name should be full name, e.g.: {'
             '  "browser_tests": ['
             '    "suite.test1", "suite.test2"'
             '  ]'
             '}'),
    'buildbucket': Property(
        default=None,
        help='The buildbucket property in which we can find build id.'
             'We need to use build id to get tests.'),
    'use_analyze': Property(
        kind=Single(bool, empty_val=False, required=False), default=True,
        help='Use analyze to skip commits that do not affect tests.'),
    'suspected_revisions': Property(
        kind=List(basestring), default=[],
        help='A list of suspected revisions from heuristic analysis.'),
}


class TestResult(object):
  SKIPPED = 'skipped'  # A commit doesn't impact the test.
  PASSED = 'passed'  # The compile or test passed.
  FAILED = 'failed'  # The compile or test failed.
  INFRA_FAILED = 'infra_failed'  # Infra failed.


def _compile_and_test_at_revision(api, target_mastername, target_buildername,
                                  target_testername, revision, requested_tests,
                                  use_analyze):
  results = {}
  with api.step.nest('test %s' % str(revision)):
    # Checkout code at the given revision to recompile.
    bot_id = {
        'mastername': target_mastername,
        'buildername': target_buildername,
        'tester': target_testername}
    bot_config = api.chromium_tests.create_generalized_bot_config_object(
        [bot_id])
    bot_update_step, bot_db = api.chromium_tests.prepare_checkout(
        bot_config, root_solution_revision=revision)

    # Figure out which test steps to run.
    all_tests, _ = api.chromium_tests.get_tests(bot_config, bot_db)
    requested_tests_to_run = [
        test for test in all_tests if test.name in requested_tests]

    # Figure out the test targets to be compiled.
    requested_test_targets = []
    for test in requested_tests_to_run:
      requested_test_targets.extend(test.compile_targets(api))
    requested_test_targets = sorted(set(requested_test_targets))

    actual_tests_to_run = requested_tests_to_run
    actual_compile_targets = requested_test_targets
    # Use dependency "analyze" to reduce tests to be run.
    if use_analyze:
      changed_files = api.findit.files_changed_by_revision(revision)

      affected_test_targets, actual_compile_targets = (
          api.filter.analyze(
              changed_files,
              test_targets=requested_test_targets,
              additional_compile_targets=[],
              config_file_name='trybot_analyze_config.json',
              mb_mastername=target_mastername,
              mb_buildername=target_buildername,
              additional_names=None))

      actual_tests_to_run = []
      for test in requested_tests_to_run:
        targets = test.compile_targets(api)
        if not targets:
          # No compile is needed for the test. Eg: checkperms.
          actual_tests_to_run.append(test)
          continue

        # Check if the test is affected by the given revision.
        for target in targets:
          if target in affected_test_targets:
            actual_tests_to_run.append(test)
            break

    if actual_compile_targets:
      api.chromium_tests.compile_specific_targets(
          bot_config,
          bot_update_step,
          bot_db,
          actual_compile_targets,
          tests_including_triggered=actual_tests_to_run,
          mb_mastername=target_mastername,
          mb_buildername=target_buildername,
          override_bot_type='builder_tester')

    # Run the tests.
    with api.chromium_tests.wrap_chromium_tests(
        bot_config, actual_tests_to_run):
      failed_tests = api.test_utils.run_tests(
          api, actual_tests_to_run,
          suffix=revision, test_filters=requested_tests)

    # Process failed tests.
    failed_tests_dict = defaultdict(list)
    for failed_test in failed_tests:
      valid = failed_test.has_valid_results(api, suffix=revision)
      results[failed_test.name] = {
          'status': TestResult.FAILED,
          'valid': valid,
      }
      if valid:
        test_list = list(failed_test.failures(api, suffix=revision))
        results[failed_test.name]['failures'] = test_list
        failed_tests_dict[failed_test.name].extend(test_list)

    # Process passed tests.
    for test in actual_tests_to_run:
      if test not in failed_tests:
        results[test.name] = {
            'status': TestResult.PASSED,
            'valid': True,
        }

    # Process skipped tests in two scenarios:
    # 1. Skipped by "analyze": tests are not affected by the given revision.
    # 2. Skipped because the requested tests don't exist at the given revision.
    for test_name in requested_tests.keys():
      if test_name not in results:
        results[test_name] = {
            'status': TestResult.SKIPPED,
            'valid': True,
        }

    return results, failed_tests_dict


def _get_reduced_test_dict(original_test_dict, failed_tests_dict):
  # Remove tests that are in both dicts from the original test dict.
  if not failed_tests_dict:
    return original_test_dict
  reduced_dict = defaultdict(list)
  for step, tests in original_test_dict.iteritems():
    if step in failed_tests_dict:
      for test in tests:
        if test not in failed_tests_dict[step]:
          reduced_dict[step].append(test)
    else:
      reduced_dict[step].extend(tests)
  return reduced_dict


def RunSteps(api, target_mastername, target_testername, good_revision,
             bad_revision, tests, buildbucket,
             use_analyze, suspected_revisions):

  if not tests:
    # tests should be saved in build parameter in this case.
    buildbucket_json = json.loads(buildbucket)
    build_id = buildbucket_json['build']['id']
    get_build_result = api.buildbucket.get_build(build_id)
    tests = json.loads(
        get_build_result.stdout['build']['parameters_json']).get(
            'additional_build_parameters', {}).get('tests')

  assert tests, 'No failed tests were specified.'

  # Figure out which builder configuration we should match for compile config.
  # Sometimes, the builder itself runs the tests and there is no tester. In
  # such cases, just treat the builder as a "tester". Thus, we default to
  # the target tester.
  tester_config = api.chromium_tests.builders.get(
      target_mastername).get('builders', {}).get(target_testername)
  target_buildername = (tester_config.get('parent_buildername') or
                        target_testername)

  # Configure to match the compile config on the builder.
  bot_config = api.chromium_tests.create_bot_config_object(
      target_mastername, target_buildername)
  api.chromium_tests.configure_build(
      bot_config, override_bot_type='builder_tester')

  # TODO(tikuta): Remove 'no_compile_py' after removing compile.py.
  for additional_config in ['goma_failfast', 'no_compile_py']:
    api.chromium.apply_config(additional_config)

  # Configure to match the test config on the tester, as builders don't have the
  # settings for swarming tests.
  if target_buildername != target_testername:
    for key, value in tester_config.get('swarming_dimensions', {}).iteritems():
      api.swarming.set_default_dimension(key, value)
  # TODO(stgao): Fix the issue that precommit=False adds the tag 'purpose:CI'.
  api.chromium_swarming.configure_swarming('chromium', precommit=False)

  # Sync to bad revision, and retrieve revisions in the regression range.
  api.chromium_tests.prepare_checkout(
      bot_config,
      root_solution_revision=bad_revision)
  revisions_to_check = api.findit.revisions_between(good_revision, bad_revision)

  suspected_revision_index = [
      revisions_to_check.index(r)
          for r in set(suspected_revisions) if r in revisions_to_check]

  # Segments revisions_to_check by suspected_revisions.
  # Each sub_range will contain following elements:
  # 1. Revision before a suspected_revision or None as a placeholder
  #    when no such revision
  # 2. Suspected_revision
  # 3. Revisions between a suspected_revision and the revision before next
  #    suspected_revision, or remaining revisions before all suspect_revisions.
  # For example, if revisions_to_check are [r0, r1, ..., r6] and
  # suspected_revisions are [r2, r5], sub_ranges will be:
  # [[None, r0], [r1, r2, r3], [r4, r5, r6]]
  if suspected_revision_index:
    # If there are consecutive revisions being suspected, include them
    # in the same sub_range by only saving the oldest revision.
    suspected_revision_index = [i for i in suspected_revision_index
                                if i - 1 not in suspected_revision_index]
    sub_ranges = []
    remaining_revisions = revisions_to_check[:]
    for index in sorted(suspected_revision_index, reverse=True):
      if index > 0:
        # try job will not run linearly, sets use_analyze to False.
        use_analyze = False
        sub_ranges.append(remaining_revisions[index - 1:])
        remaining_revisions = remaining_revisions[:index - 1]
    # None is a placeholder for the last known good revision.
    sub_ranges.append([None] + remaining_revisions)
  else:
    # Treats the entire regression range as a single sub-range.
    sub_ranges = [[None] + revisions_to_check]

  test_results = {}
  try_job_metadata = {
      'regression_range_size': len(revisions_to_check)
  }
  report = {
      'result': test_results,
      'metadata': try_job_metadata
  }

  revision_being_checked = None
  try:
    culprits = defaultdict(dict)
    # Tests that haven't found culprits in tested revision(s).
    tests_have_not_found_culprit = tests
    # Iterates through sub_ranges and find culprits for each failed test.
    # Sub-ranges with newer revisions are tested first so we have better chance
    # that try job will reproduce exactly the same failure as in waterfall.
    for sub_range in sub_ranges:
      if not tests_have_not_found_culprit:  # All tests have found culprits.
        break

      # The revision right before the suspected revision provided by
      # the heuristic result.
      potential_green_rev = sub_range[0]
      following_revisions = sub_range[1:]
      if potential_green_rev:
        revision_being_checked = potential_green_rev
        test_results[potential_green_rev], tests_failed_in_potential_green = (
            _compile_and_test_at_revision(
                api, target_mastername, target_buildername, target_testername,
                potential_green_rev,tests_have_not_found_culprit, use_analyze))
      else:
        tests_failed_in_potential_green = {}

      tests_passed_in_potential_green = _get_reduced_test_dict(
         tests_have_not_found_culprit, tests_failed_in_potential_green)

      # Culprits for tests that failed in potential green should be earlier, so
      # removes passed tests and only runs failed ones in following revisions.
      if tests_passed_in_potential_green:
        tests_to_run = tests_passed_in_potential_green
        for revision in following_revisions:
          revision_being_checked = revision
          # Since tests_to_run are tests that passed in previous revision,
          # whichever test that fails now will find current revision is the
          # culprit.
          test_results[revision], tests_failed_in_revision = (
              _compile_and_test_at_revision(
                  api, target_mastername, target_buildername, target_testername,
                  revision, tests_to_run, use_analyze))

          # Removes tests that passed in potential green and failed in
          # following revisions: culprits have been found for them.
          tests_have_not_found_culprit = _get_reduced_test_dict(
              tests_have_not_found_culprit, tests_failed_in_revision)

          # Only runs tests that have not found culprits in later revisions.
          tests_to_run = _get_reduced_test_dict(
              tests_to_run, tests_failed_in_revision)

          # Records found culprits.
          for step, test_list in tests_failed_in_revision.iteritems():
            for test in test_list:
              culprits[step][test] = revision

          if not tests_to_run:
            break

  except api.step.InfraFailure:
    test_results[revision_being_checked] = TestResult.INFRA_FAILED
    report['metadata']['infra_failure'] = True
    raise
  finally:
    if culprits:
      report['culprits'] = culprits

    # Give the full report including test results and metadata.
    step_result = api.python.succeeding_step(
        'report', [json.dumps(report, indent=2)], as_log='report')

    # Set the report as a build property too, so that it will be reported back
    # to Buildbucket and Findit will pull from there instead of buildbot master.
    step_result.presentation.properties['report'] = report

  return report


def GenTests(api):
  def props(
      tests, platform_name, tester_name, use_analyze=False, good_revision=None,
      bad_revision=None, suspected_revisions=None, buildbucket=None):
    properties = {
        'path_config': 'kitchen',
        'mastername': 'tryserver.chromium.%s' % platform_name,
        'buildername': '%s_chromium_variable' % platform_name,
        'slavename': 'build1-a1',
        'buildnumber': 1,
        'target_mastername': 'chromium.%s' % platform_name,
        'target_testername': tester_name,
        'good_revision': good_revision or 'r0',
        'bad_revision': bad_revision or 'r1',
        'use_analyze': use_analyze,
    }
    if tests:
      properties['tests'] = tests
    if suspected_revisions:
      properties['suspected_revisions'] = suspected_revisions
    if buildbucket:
      properties['buildbucket'] = buildbucket
    return api.properties(**properties) + api.platform.name(platform_name)

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

  def simulated_buildbucket_output(additional_build_parameters):
    buildbucket_output = {
        'build':{
          'parameters_json': json.dumps(additional_build_parameters)
        }
    }

    return api.buildbucket.step_data(
        'buildbucket.get',
        stdout=api.raw_io.output(json.dumps(buildbucket_output)))

  yield (
      api.test('nonexistent_test_step_skipped') +
      props({'newly_added_tests': ['Test.One', 'Test.Two', 'Test.Three']},
            'win', 'Win7 Tests (1)') +
      api.override_step_data(
          'test r1.read test spec (chromium.win.json)',
          api.json.output({
              'Win7 Tests (1)': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      )
  )

  yield (
      api.test('unaffected_test_skipped_by_analyze') +
      props({'affected_tests': ['Test.One'], 'unaffected_tests': ['Test.Two']},
            'win', 'Win7 Tests (1)', use_analyze=True) +
      api.override_step_data(
          'test r1.read test spec (chromium.win.json)',
          api.json.output({
              'Win7 Tests (1)': {
                  'gtest_tests': [
                      {
                        'test': 'affected_tests',
                        'swarming': {'can_use_on_swarming_builders': True},
                      },
                      {
                        'test': 'unaffected_tests',
                        'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r1.analyze',
          api.json.output({
              'status': 'Found dependency',
              'compile_targets': ['affected_tests', 'affected_tests_run'],
              'test_targets': ['affected_tests', 'affected_tests_run'],
          })
      ) +
      api.override_step_data(
          'test r1.affected_tests (r1)',
          simulated_gtest_output(passed_test_names=['Test.One'])
      )
  )

  yield (
      api.test('test_without_targets_not_skipped') +
      props({'unaffected_tests': ['Test.One'], 'checkperms': []},
            'win', 'Win7 Tests (1)', use_analyze=True) +
      api.override_step_data(
          'test r1.read test spec (chromium.win.json)',
          api.json.output({
              'Win7 Tests (1)': {
                  'gtest_tests': [
                      {
                        'test': 'unaffected_tests',
                        'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
                  'scripts': [
                      {
                          'name': 'checkperms',
                          'script': 'checkperms.py'
                      },
                  ]
              },
          })
      ) +
      api.override_step_data(
          'test r1.analyze',
          api.json.output({
              'status': 'No dependencies',
              'compile_targets': [],
              'test_targets': [],
          })
      )
  )

  yield (
      api.test('all_test_failed') +
      props({'gl_tests': ['Test.One', 'Test.Two', 'Test.Three']},
            'win', 'Win7 Tests (1)') +
      api.override_step_data(
          'test r1.read test spec (chromium.win.json)',
          api.json.output({
              'Win7 Tests (1)': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r1.gl_tests (r1)',
          simulated_gtest_output(
              failed_test_names=['Test.One', 'Test.Two', 'Test.Three'])
      )
  )

  yield (
      api.test('all_test_passed') +
      props({'gl_tests': ['Test.One', 'Test.Two', 'Test.Three']},
            'win', 'Win7 Tests (1)') +
      api.override_step_data(
          'test r1.read test spec (chromium.win.json)',
          api.json.output({
              'Win7 Tests (1)': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r1.gl_tests (r1)',
          simulated_gtest_output(
              passed_test_names=['Test.One', 'Test.Two', 'Test.Three'])
      )
  )

  yield (
      api.test('only_one_test_passed') +
      props({'gl_tests': ['Test.One', 'Test.Two', 'Test.Three']},
            'win', 'Win7 Tests (1)') +
      api.override_step_data(
          'test r1.read test spec (chromium.win.json)',
          api.json.output({
              'Win7 Tests (1)': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r1.gl_tests (r1)',
          simulated_gtest_output(
              failed_test_names=['Test.One', 'Test.Two'],
              passed_test_names=['Test.Three'])
      )
  )

  yield (
      api.test('compile_skipped') +
      props({'checkperms': []}, 'win', 'Win7 Tests (1)') +
      api.override_step_data(
          'test r1.read test spec (chromium.win.json)',
          api.json.output({
              'Win7 Tests (1)': {
                  'scripts': [
                      {
                          'name': 'checkperms',
                          'script': 'checkperms.py'
                      },
                  ]
              },
          })
      )
  )

  yield (
      api.test('none_swarming_tests') +
      props({'gl_tests': ['Test.One', 'Test.Two', 'Test.Three']},
            'win', 'Win7 Tests (1)') +
      api.override_step_data(
          'test r1.read test spec (chromium.win.json)',
          api.json.output({
              'Win7 Tests (1)': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': False},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r1.gl_tests (r1)',
          simulated_gtest_output(
              failed_test_names=['Test.One', 'Test.Two'],
              passed_test_names=['Test.Three'])
      )
  )

  yield (
      api.test('swarming_tests') +
      props({'gl_tests': ['Test.One']}, 'mac', 'Mac10.9 Tests') +
      api.override_step_data(
          'test r1.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r1.gl_tests (r1)',
          simulated_gtest_output(passed_test_names=['Test.One'])
      )
  )

  yield (
      api.test('findit_culprit_in_last_sub_range') +
      props(
          {'gl_tests': ['Test.One']}, 'mac', 'Mac10.9 Tests', use_analyze=False,
           good_revision='r0', bad_revision='r6', suspected_revisions=['r3']) +
      api.override_step_data(
          'test r2.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r3.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output(
              '\n'.join('r%d' % i for i in reversed(range(1, 7))))) +
      api.override_step_data(
          'test r2.gl_tests (r2)',
          simulated_gtest_output(passed_test_names=['Test.One'])) +
      api.override_step_data(
          'test r3.gl_tests (r3)',
          simulated_gtest_output(failed_test_names=['Test.One']))
  )

  yield (
      api.test('findit_culprit_in_middle_sub_range') +
      props(
          {'gl_tests': ['Test.One']}, 'mac', 'Mac10.9 Tests', use_analyze=False,
           good_revision='r0', bad_revision='r6',
           suspected_revisions=['r3', 'r6']) +
      api.override_step_data(
          'test r2.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r3.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r5.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r6.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output(
              '\n'.join('r%d' % i for i in reversed(range(1, 7))))) +
      api.override_step_data(
          'test r2.gl_tests (r2)',
          simulated_gtest_output(passed_test_names=['Test.One'])) +
      api.override_step_data(
          'test r3.gl_tests (r3)',
          simulated_gtest_output(failed_test_names=['Test.One'])) +
      api.override_step_data(
          'test r5.gl_tests (r5)',
          simulated_gtest_output(passed_test_names=['Test.One'])) +
      api.override_step_data(
          'test r6.gl_tests (r6)',
          simulated_gtest_output(passed_test_names=['Test.One']))
  )

  yield (
      api.test('findit_culprit_in_first_sub_range') +
      props(
          {'gl_tests': ['Test.One']}, 'mac', 'Mac10.9 Tests', use_analyze=False,
           good_revision='r0', bad_revision='r6',
           suspected_revisions=['r6']) +
      api.override_step_data(
          'test r1.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r5.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r6.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output(
              '\n'.join('r%d' % i for i in reversed(range(1, 7))))) +
      api.override_step_data(
          'test r1.gl_tests (r1)',
          simulated_gtest_output(failed_test_names=['Test.One'])) +
      api.override_step_data(
          'test r5.gl_tests (r5)',
          simulated_gtest_output(passed_test_names=['Test.One'])) +
      api.override_step_data(
          'test r6.gl_tests (r6)',
          simulated_gtest_output(passed_test_names=['Test.One']))
  )

  yield (
      api.test('findit_steps_multiple_culprits') +
      props(
          {'gl_tests': ['Test.gl_One'], 'browser_tests': ['Test.browser_One']},
          'mac', 'Mac10.9 Tests', use_analyze=False,
           good_revision='r0', bad_revision='r6',
           suspected_revisions=['r3','r6']) +
      api.override_step_data(
          'test r2.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                      {
                          'test': 'browser_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r3.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                      {
                          'test': 'browser_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r5.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                      {
                          'test': 'browser_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r6.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                      {
                          'test': 'browser_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output(
              '\n'.join('r%d' % i for i in reversed(range(1, 7))))) +
      api.override_step_data(
          'test r5.gl_tests (r5)',
          simulated_gtest_output(failed_test_names=['Test.gl_One'])) +
      api.override_step_data(
          'test r5.browser_tests (r5)',
          simulated_gtest_output(passed_test_names=['Test.browser_One'])) +
      api.override_step_data(
          'test r6.browser_tests (r6)',
          simulated_gtest_output(failed_test_names=['Test.browser_One']))+
      api.override_step_data(
          'test r2.gl_tests (r2)',
          simulated_gtest_output(passed_test_names=['Test.gl_One'])) +
      api.override_step_data(
          'test r3.gl_tests (r3)',
          simulated_gtest_output(failed_test_names=['Test.gl_One']))
  )

  yield (
      api.test('findit_tests_multiple_culprits') +
      props(
          {'gl_tests': ['Test.One', 'Test.Two', 'Test.Three']},
          'mac', 'Mac10.9 Tests', use_analyze=False,
           good_revision='r0', bad_revision='r6',
           suspected_revisions=['r3', 'r5']) +
      api.override_step_data(
          'test r2.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r3.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r4.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r5.read test spec (chromium.mac.json)', api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r6.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output(
              '\n'.join('r%d' % i for i in reversed(range(1, 7))))) +
      api.override_step_data(
          'test r4.gl_tests (r4)',
          simulated_gtest_output(passed_test_names=['Test.One', 'Test.Three'],
                                 failed_test_names=['Test.Two'])) +
      api.override_step_data(
          'test r5.gl_tests (r5)',
          simulated_gtest_output(passed_test_names=['Test.One'],
                                 failed_test_names=['Test.Three'])) +
      api.override_step_data(
          'test r6.gl_tests (r6)',
          simulated_gtest_output(failed_test_names=['Test.One']))+
      api.override_step_data(
          'test r2.gl_tests (r2)',
          simulated_gtest_output(passed_test_names=['Test.Two'])) +
      api.override_step_data(
          'test r3.gl_tests (r3)',
          simulated_gtest_output(failed_test_names=['Test.Two']))
  )

  yield (
      api.test('findit_consecutive_culprits') +
      props(
          {'gl_tests': ['Test.One']},
          'mac', 'Mac10.9 Tests', use_analyze=False,
           good_revision='r0', bad_revision='r6',
           suspected_revisions=['r3', 'r4']) +
      api.override_step_data(
          'test r2.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r3.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r4.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output(
              '\n'.join('r%d' % i for i in reversed(range(1, 7))))) +
      api.override_step_data(
          'test r4.gl_tests (r4)',
          simulated_gtest_output(failed_test_names=['Test.One'])) +
      api.override_step_data(
          'test r2.gl_tests (r2)',
          simulated_gtest_output(passed_test_names=['Test.One'])) +
      api.override_step_data(
          'test r3.gl_tests (r3)',
          simulated_gtest_output(passed_test_names=['Test.One']))
  )

  yield (
      api.test('record_infra_failure') +
      props({'gl_tests': ['Test.One']}, 'mac', 'Mac10.9 Tests') +
      api.override_step_data(
          'test r1.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r1.preprocess_for_goma.start_goma', retcode=1) +
      api.override_step_data(
          'test r1.preprocess_for_goma.goma_jsonstatus',
          stdout=api.json.output({
              'notice': [
                  {
                      'infra_status': {
                          'ping_status_code': 408,
                      },
                  },
              ],
          }))
  )

  yield (
      api.test('use_build_parameter_for_tests') +
      props({}, 'mac', 'Mac10.9 Tests', use_analyze=False,
            good_revision='r0', bad_revision='r6',
            suspected_revisions=['r3', 'r4'],
            buildbucket=json.dumps({'build': {'id': 'id1'}})) +
      simulated_buildbucket_output({
          'additional_build_parameters' : {
              'tests': {
                  'gl_tests': ['Test.One']
              }
          }}) +
      api.override_step_data(
          'test r2.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r3.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r4.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output(
              '\n'.join('r%d' % i for i in reversed(range(1, 7))))) +
      api.override_step_data(
          'test r4.gl_tests (r4)',
          simulated_gtest_output(failed_test_names=['Test.One'])) +
      api.override_step_data(
          'test r2.gl_tests (r2)',
          simulated_gtest_output(passed_test_names=['Test.One'])) +
      api.override_step_data(
          'test r3.gl_tests (r3)',
          simulated_gtest_output(passed_test_names=['Test.One']))
  )

  yield (
      api.test('use_analyze_set_to_False_for_non_linear_try_job') +
      props(
          {'gl_tests': ['Test.One']}, 'mac', 'Mac10.9 Tests', use_analyze=True,
           good_revision='r0', bad_revision='r6', suspected_revisions=['r3']) +
      api.override_step_data(
          'test r2.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r3.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.9 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output(
              '\n'.join('r%d' % i for i in reversed(range(1, 7))))) +
      api.override_step_data(
          'test r2.gl_tests (r2)',
          simulated_gtest_output(passed_test_names=['Test.One'])) +
      api.override_step_data(
          'test r3.gl_tests (r3)',
          simulated_gtest_output(failed_test_names=['Test.One']))
  )
