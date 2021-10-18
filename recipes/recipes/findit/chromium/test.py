# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from collections import defaultdict
import six

from recipe_engine.config import Dict
from recipe_engine.config import List
from recipe_engine.config import Single
from recipe_engine.recipe_api import Property

from RECIPE_MODULES.build import chromium


PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'builder_group',
    'chromium_swarming',
    'chromium_tests',
    'findit',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/legacy_annotation',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'test_utils',
]

import re

from recipe_engine import post_process


PROPERTIES = {
    'target_testername':
        Property(
            kind=str,
            help='The target tester to match test config to. If the tests are '
            'run on a builder, just treat the builder as a tester.'),
    'good_revision':
        Property(kind=str, help='The last known good revision.'),
    'bad_revision':
        Property(kind=str, help='The first known good revision.'),
    'tests':
        Property(
            kind=Dict(value_type=list),
            default={},
            help='The failed tests, the test name should be full name, e.g.: {'
            '  "browser_tests": ['
            '    "suite.test1", "suite.test2"'
            '  ]'
            '}'),
    'use_analyze':
        Property(
            kind=Single(bool, empty_val=False, required=False),
            default=True,
            help='Use analyze to skip commits that do not affect tests.'),
    'suspected_revisions':
        Property(
            kind=List(six.string_types),
            default=[],
            help='A list of suspected revisions from heuristic analysis.'),
    'test_on_good_revision':
        Property(
            kind=Single(bool, empty_val=False, required=False),
            default=True,
            help='Run test on good revision as well if the first revision '
            'in range is suspected.'),
    'test_repeat_count':
        Property(
            kind=Single(int, required=False),
            default=20,
            help='How many times to repeat the tests.'),
}


def _get_reduced_test_dict(original_test_dict, failed_tests_dict):
  # Remove tests that are in both dicts from the original test dict.
  if not failed_tests_dict:
    return original_test_dict
  reduced_dict = defaultdict(list)
  for step, tests in original_test_dict.iteritems():
    remain_tests = list(set(tests) - set(failed_tests_dict.get(step, [])))
    if remain_tests:
      reduced_dict[step] = remain_tests
  return reduced_dict


def _get_flaky_tests(test_results):
  # Uses pass_fail_count to get flaky tests.
  flaky_tests = defaultdict(list)
  if not test_results:
    return flaky_tests

  for step, result in test_results.iteritems():
    pass_fail_counts = result.get('pass_fail_counts')
    if not pass_fail_counts:
      continue
    for test, test_counts in pass_fail_counts.iteritems():
      if test_counts.get('pass_count') and test_counts.get('fail_count'):
        flaky_tests[step].append(test)

  return flaky_tests


def _consolidate_flaky_tests(all_flakes, new_flakes):
  for step, tests in new_flakes.iteritems():
    all_flakes[step] = list(set(all_flakes[step]) | set(tests))


def RunSteps(api, target_testername, good_revision, bad_revision, tests,
             use_analyze, suspected_revisions, test_on_good_revision,
             test_repeat_count):
  assert tests, 'No failed tests were specified.'
  target_builder_group = api.builder_group.for_target
  target_tester_id = chromium.BuilderId.create_for_group(
      target_builder_group, target_testername)
  bot_mirror, checked_out_revision, cached_revision = (
      api.findit.configure_and_sync(target_tester_id, bad_revision))

  # retrieve revisions in the regression range.
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
        # TODO(https://crbug.com/874292): filter out irrelevant commits first.
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
      'metadata': try_job_metadata,
      'previously_checked_out_revision': checked_out_revision,
      'previously_cached_revision': cached_revision
  }

  revision_being_checked = None
  found = False
  flakes = defaultdict(list)
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
      first_revision = sub_range[0]
      following_revisions = sub_range[1:]
      if first_revision:
        revision_being_checked = first_revision
        # Should not use "analyze" to skip tests at the first revision, because
        # if a skipped test fails at the second revision in the sub range, the
        # second revision is not necessarily the culprit.
        (test_results[first_revision], tests_failed_in_potential_green,
         compile_failure) = api.findit.compile_and_test_at_revision(
             bot_mirror,
             first_revision,
             tests_have_not_found_culprit,
             use_analyze=False,
             test_repeat_count=test_repeat_count)
        if compile_failure:
          return compile_failure
      else:
        tests_failed_in_potential_green = {}

      # Looks for reliably failed tests.
      flaky_tests_in_potential_green = _get_flaky_tests(test_results.get(
          first_revision))
      _consolidate_flaky_tests(flakes, flaky_tests_in_potential_green)
      tests_passed_in_potential_green = _get_reduced_test_dict(
          tests_have_not_found_culprit, tests_failed_in_potential_green
      )

      # Culprits for tests that failed in potential green should be earlier, so
      # removes failed tests and only runs passed ones in following revisions.
      if tests_passed_in_potential_green:
        tests_to_run = tests_passed_in_potential_green
        for revision in following_revisions:
          revision_being_checked = revision
          # Since tests_to_run are tests that passed in previous revision,
          # whichever test that fails now will find current revision is the
          # culprit.
          test_results[revision], tests_failed_in_revision, compile_failure = (
              api.findit.compile_and_test_at_revision(bot_mirror, revision,
                                                      tests_to_run, use_analyze,
                                                      test_repeat_count))
          if compile_failure:
            return compile_failure

          flaky_tests_in_revision = _get_flaky_tests(test_results[revision])
          reliable_failed_tests_in_revision = _get_reduced_test_dict(
            tests_failed_in_revision, flaky_tests_in_revision)
          _consolidate_flaky_tests(flakes, flaky_tests_in_revision)
          # Removes tests that passed in potential green and failed in
          # following revisions: culprits have been found for them.
          tests_have_not_found_culprit = _get_reduced_test_dict(
              tests_have_not_found_culprit, tests_failed_in_revision)

          # Only runs tests that have not found culprits in later revisions.
          tests_to_run = _get_reduced_test_dict(
              tests_to_run, tests_failed_in_revision)

          # Records found culprits.
          for step, test_list in reliable_failed_tests_in_revision.iteritems():
            for test in test_list:
              culprits[step][test] = revision

          if not tests_to_run:
            break

    if culprits and test_on_good_revision:
      # Need to deflake by running on good revision.
      tests_run_on_good_revision = defaultdict(list)
      for step, step_culprits in culprits.iteritems():
        for test, test_culprit in step_culprits.iteritems():
          if test_culprit == revisions_to_check[0]:
            tests_run_on_good_revision[step].append(test)

      if tests_run_on_good_revision:
        (test_results[good_revision], tests_failed_in_revision,
         compile_failure) = api.findit.compile_and_test_at_revision(
             bot_mirror, good_revision, tests_run_on_good_revision, use_analyze,
             test_repeat_count)
        if compile_failure:
          return compile_failure
        if tests_failed_in_revision:
          # Some tests also failed on good revision, they should be flaky.
          # Should remove them from culprits.
          new_culprits = defaultdict(dict)
          for step, step_culprits in culprits.iteritems():
            for test, test_culprit in step_culprits.iteritems():
              if test in tests_failed_in_revision.get(step, []):
                continue
              new_culprits[step][test] = test_culprit
          culprits = new_culprits
          _consolidate_flaky_tests(flakes, tests_failed_in_revision)

    found = bool(culprits)

  except api.step.InfraFailure:
    test_results[revision_being_checked] = api.findit.TestResult.INFRA_FAILED
    report['metadata']['infra_failure'] = True
    raise
  finally:
    report['last_checked_out_revision'] = api.properties.get('got_revision')
    if found:
      report['culprits'] = culprits

    if flakes:
      report['flakes'] = flakes

    # Give the full report including test results and metadata.
    api.python.succeeding_step(
        'report', [api.json.dumps(report, indent=2)], as_log='report')


def GenTests(api):
  def base(
      tests, platform_name, tester_name, use_analyze=False, good_revision=None,
      bad_revision=None, suspected_revisions=None,
      test_on_good_revision=True, test_repeat_count=20):
    properties = {
        'bot_id': 'build1-a1',
        'target_testername': tester_name,
        'good_revision': good_revision or 'r0',
        'bad_revision': bad_revision or 'r1',
        'use_analyze': use_analyze,
        'test_on_good_revision': test_on_good_revision,
        'test_repeat_count': test_repeat_count,
    }
    if tests:
      properties['tests'] = tests
    if suspected_revisions:
      properties['suspected_revisions'] = suspected_revisions
    return sum([
        api.properties(**properties),
        api.buildbucket.ci_build(
            builder='findit_variable',
            git_repo='https://chromium.googlesource.com/chromium/src',
        ),
        api.builder_group.for_current('tryserver.chromium.%s' % platform_name),
        api.builder_group.for_target('chromium.%s' % platform_name),
        api.platform.name(platform_name),
    ], api.empty_test_data())

  def verify_report_fields(check, step_odict, expected_report_fields):
    """Verifies fields in report are with expected values."""
    step = step_odict['report']
    report_dict = api.json.loads(step.logs['report'])

    def check_fields(expected_fields, actual_fields):
      for key, value in expected_fields.iteritems():
        if value and isinstance(value, dict):
          check_fields(value, actual_fields.get(key) or {})
        else:
          check(actual_fields.get(key) == value)

    check_fields(expected_report_fields, report_dict)

    return step_odict

  yield api.test(
      'nonexistent_test_step_skipped',
      base({
          'newly_added_tests': ['Test.One', 'Test.Two', 'Test.Three']
      }, 'win', 'Win7 Tests (1)'),
      api.chromium_tests.read_source_side_spec(
          'chromium.win', {
              'Win7 Tests (1)': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r1.'),
  )

  yield api.test(
      'unaffected_test_skipped_by_analyze',
      base({
          'affected_tests': ['Test.One'],
          'unaffected_tests': ['Test.Two']
      },
           'win',
           'Win7 Tests (1)',
           use_analyze=True),
      api.chromium_tests.read_source_side_spec(
          'chromium.win', {
              'Win7 Tests (1)': {
                  'gtest_tests': [
                      {
                          'test': 'affected_tests',
                          'swarming': {
                              'can_use_on_swarming_builders': True
                          },
                      },
                      {
                          'test': 'unaffected_tests',
                          'swarming': {
                              'can_use_on_swarming_builders': True
                          },
                      },
                  ],
              },
          },
          step_prefix='test r1.'),
      api.override_step_data(
          'test r1.analyze',
          api.json.output({
              'status': 'Found dependency',
              'compile_targets': ['affected_tests', 'affected_tests_run'],
              'test_targets': ['affected_tests', 'affected_tests_run'],
          })),
      api.override_step_data(
          'test r1.affected_tests (r1)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  passed_test_names=['Test.One']))),
  )

  yield api.test(
      'test_without_targets_not_skipped',
      base({
          'unaffected_tests': ['Test.One'],
          'checkperms': []
      },
           'win',
           'Win7 Tests (1)',
           use_analyze=True),
      api.chromium_tests.read_source_side_spec(
          'chromium.win', {
              'Win7 Tests (1)': {
                  'gtest_tests': [{
                      'test': 'unaffected_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
                  'scripts': [{
                      'name': 'checkperms',
                      'script': 'checkperms.py'
                  },]
              },
          },
          step_prefix='test r1.'),
      api.override_step_data(
          'test r1.analyze',
          api.json.output({
              'status': 'No dependencies',
              'compile_targets': [],
              'test_targets': [],
          })),
  )

  yield api.test(
      'all_test_failed',
      base({
          'gl_tests': ['Test.One', 'Test.Two', 'Test.Three']
      },
           'win',
           'Win7 Tests (1)',
           test_on_good_revision=False),
      api.chromium_tests.read_source_side_spec(
          'chromium.win', {
              'Win7 Tests (1)': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r1.'),
      api.override_step_data(
          'test r1.gl_tests (r1)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  failed_test_names=['Test.One', 'Test.Two', 'Test.Three']),
              failure=True)),
  )

  yield api.test(
      'all_test_passed',
      base({
          'gl_tests': ['Test.One', 'Test.Two', 'Test.Three']
      }, 'win', 'Win7 Tests (1)'),
      api.chromium_tests.read_source_side_spec(
          'chromium.win', {
              'Win7 Tests (1)': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r1.'),
      api.override_step_data(
          'test r1.gl_tests (r1)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  passed_test_names=['Test.One', 'Test.Two', 'Test.Three']))),
  )

  yield api.test(
      'only_one_test_passed',
      base({
          'gl_tests': ['Test.One', 'Test.Two', 'Test.Three']
      }, 'win', 'Win7 Tests (1)'),
      api.chromium_tests.read_source_side_spec(
          'chromium.win', {
              'Win7 Tests (1)': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r0.'),
      api.override_step_data(
          'test r0.gl_tests (r0)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  passed_test_names=['Test.One', 'Test.Two']),
              failure=True)),
      api.chromium_tests.read_source_side_spec(
          'chromium.win', {
              'Win7 Tests (1)': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r1.'),
      api.override_step_data(
          'test r1.gl_tests (r1)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  failed_test_names=['Test.One', 'Test.Two'],
                  passed_test_names=['Test.Three']),
              failure=True)),
  )

  yield api.test(
      'compile_skipped',
      base({
          'checkperms': []
      }, 'win', 'Win7 Tests (1)'),
      api.chromium_tests.read_source_side_spec(
          'chromium.win', {
              'Win7 Tests (1)': {
                  'scripts': [{
                      'name': 'checkperms',
                      'script': 'checkperms.py'
                  },]
              },
          },
          step_prefix='test r1.'),
  )

  yield api.test(
      'none_swarming_tests',
      base({
          'gl_tests': ['Test.One', 'Test.Two', 'Test.Three']
      },
           'win',
           'Win7 Tests (1)',
           test_on_good_revision=False),
      api.chromium_tests.read_source_side_spec(
          'chromium.win', {
              'Win7 Tests (1)': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': False
                      },
                  },],
              },
          },
          step_prefix='test r1.'),
      api.override_step_data(
          'test r1.gl_tests (r1)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  failed_test_names=['Test.One', 'Test.Two'],
                  passed_test_names=['Test.Three']),
              failure=True), api.legacy_annotation.success_step),
  )

  yield api.test(
      'swarming_tests',
      base({
          'gl_tests': ['Test.One']
      }, 'mac', 'Mac10.13 Tests'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r1.'),
      api.override_step_data(
          'test r1.gl_tests (r1)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  passed_test_names=['Test.One']))),
  )

  yield api.test(
      'findit_culprit_in_last_sub_range',
      base({
          'gl_tests': ['Test.One']
      },
           'mac',
           'Mac10.13 Tests',
           use_analyze=False,
           good_revision='r0',
           bad_revision='r6',
           suspected_revisions=['r3']),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r2.'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r3.'),
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output('\n'.join(
              'r%d' % i for i in reversed(range(1, 7))))),
      api.override_step_data(
          'test r2.gl_tests (r2)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  passed_test_names=['Test.One']))),
      api.override_step_data(
          'test r3.gl_tests (r3)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  failed_test_names=['Test.One']),
              failure=True)),
  )

  yield api.test(
      'findit_culprit_in_middle_sub_range',
      base({
          'gl_tests': ['Test.One']
      },
           'mac',
           'Mac10.13 Tests',
           use_analyze=False,
           good_revision='r0',
           bad_revision='r6',
           suspected_revisions=['r3', 'r6']),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r2.'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r3.'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r5.'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r6.'),
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output('\n'.join(
              'r%d' % i for i in reversed(range(1, 7))))),
      api.override_step_data(
          'test r2.gl_tests (r2)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  passed_test_names=['Test.One']))),
      api.override_step_data(
          'test r3.gl_tests (r3)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  failed_test_names=['Test.One']),
              failure=True)),
      api.override_step_data(
          'test r5.gl_tests (r5)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  passed_test_names=['Test.One']),
              failure=True)),
      api.override_step_data(
          'test r6.gl_tests (r6)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  passed_test_names=['Test.One']))),
  )

  yield api.test(
      'findit_culprit_in_first_sub_range',
      base({
          'gl_tests': ['Test.One']
      },
           'mac',
           'Mac10.13 Tests',
           use_analyze=False,
           good_revision='r0',
           bad_revision='r6',
           suspected_revisions=['r6'],
           test_on_good_revision=False),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r1.'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r5.'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r6.'),
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output('\n'.join(
              'r%d' % i for i in reversed(range(1, 7))))),
      api.override_step_data(
          'test r1.gl_tests (r1)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  failed_test_names=['Test.One']),
              failure=True)),
      api.override_step_data(
          'test r5.gl_tests (r5)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  passed_test_names=['Test.One']))),
      api.override_step_data(
          'test r6.gl_tests (r6)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  passed_test_names=['Test.One']))),
  )

  yield api.test(
      'findit_steps_multiple_culprits',
      base({
          'gl_tests': ['Test.gl_One'],
          'browser_tests': ['Test.browser_One']
      },
           'mac',
           'Mac10.13 Tests',
           use_analyze=False,
           good_revision='r0',
           bad_revision='r6',
           suspected_revisions=['r3', 'r6']),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {
                              'can_use_on_swarming_builders': True
                          },
                      },
                      {
                          'test': 'browser_tests',
                          'swarming': {
                              'can_use_on_swarming_builders': True
                          },
                      },
                  ],
              },
          },
          step_prefix='test r2.'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {
                              'can_use_on_swarming_builders': True
                          },
                      },
                      {
                          'test': 'browser_tests',
                          'swarming': {
                              'can_use_on_swarming_builders': True
                          },
                      },
                  ],
              },
          },
          step_prefix='test r3.'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {
                              'can_use_on_swarming_builders': True
                          },
                      },
                      {
                          'test': 'browser_tests',
                          'swarming': {
                              'can_use_on_swarming_builders': True
                          },
                      },
                  ],
              },
          },
          step_prefix='test r5.'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {
                              'can_use_on_swarming_builders': True
                          },
                      },
                      {
                          'test': 'browser_tests',
                          'swarming': {
                              'can_use_on_swarming_builders': True
                          },
                      },
                  ],
              },
          },
          step_prefix='test r6.'),
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output('\n'.join(
              'r%d' % i for i in reversed(range(1, 7))))),
      api.override_step_data(
          'test r5.gl_tests (r5)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  failed_test_names=['Test.gl_One']),
              failure=True)),
      api.override_step_data(
          'test r5.browser_tests (r5)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  passed_test_names=['Test.browser_One']))),
      api.override_step_data(
          'test r6.browser_tests (r6)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  failed_test_names=['Test.browser_One']),
              failure=True)),
      api.override_step_data(
          'test r2.gl_tests (r2)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  passed_test_names=['Test.gl_One']))),
      api.override_step_data(
          'test r3.gl_tests (r3)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  failed_test_names=['Test.gl_One']),
              failure=True)),
  )

  yield api.test(
      'findit_tests_multiple_culprits',
      base({
          'gl_tests': ['Test.One', 'Test.Two', 'Test.Three']
      },
           'mac',
           'Mac10.13 Tests',
           use_analyze=False,
           good_revision='r0',
           bad_revision='r6',
           suspected_revisions=['r3', 'r5']),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r2.'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r3.'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r4.'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r5.'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r6.'),
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output('\n'.join(
              'r%d' % i for i in reversed(range(1, 7))))),
      api.override_step_data(
          'test r4.gl_tests (r4)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  passed_test_names=['Test.One', 'Test.Three'],
                  failed_test_names=['Test.Two']),
              failure=True)),
      api.override_step_data(
          'test r5.gl_tests (r5)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  passed_test_names=['Test.One'],
                  failed_test_names=['Test.Three']),
              failure=True)),
      api.override_step_data(
          'test r6.gl_tests (r6)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  failed_test_names=['Test.One']),
              failure=True)),
      api.override_step_data(
          'test r2.gl_tests (r2)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  passed_test_names=['Test.Two']))),
      api.override_step_data(
          'test r3.gl_tests (r3)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  failed_test_names=['Test.Two']),
              failure=True)),
  )

  yield api.test(
      'findit_consecutive_culprits',
      base({
          'gl_tests': ['Test.One']
      },
           'mac',
           'Mac10.13 Tests',
           use_analyze=False,
           good_revision='r0',
           bad_revision='r6',
           suspected_revisions=['r3', 'r4']),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r2.'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r3.'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r4.'),
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output('\n'.join(
              'r%d' % i for i in reversed(range(1, 7))))),
      api.override_step_data(
          'test r4.gl_tests (r4)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  failed_test_names=['Test.One']),
              failure=True)),
      api.override_step_data(
          'test r2.gl_tests (r2)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  passed_test_names=['Test.One']))),
      api.override_step_data(
          'test r3.gl_tests (r3)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  passed_test_names=['Test.One']))),
  )

  yield api.test(
      'record_infra_failure',
      base({
          'gl_tests': ['Test.One']
      }, 'mac', 'Mac10.13 Tests'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r1.'),
      api.override_step_data(
          'test r1.preprocess_for_goma.start_goma', retcode=1),
      api.step_data(
          'test r1.preprocess_for_goma.goma_jsonstatus',
          api.json.output(data={
              'notice': [{
                  'infra_status': {
                      'ping_status_code': 408,
                  },
              },],
          })),
  )

  yield api.test(
      'use_analyze_set_to_False_for_non_linear_try_job',
      base({
          'gl_tests': ['Test.One']
      },
           'mac',
           'Mac10.13 Tests',
           use_analyze=True,
           good_revision='r0',
           bad_revision='r6',
           suspected_revisions=['r3']),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r2.'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r3.'),
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output('\n'.join(
              'r%d' % i for i in reversed(range(1, 7))))),
      api.override_step_data(
          'test r2.gl_tests (r2)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  passed_test_names=['Test.One']))),
      api.override_step_data(
          'test r3.gl_tests (r3)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  failed_test_names=['Test.One']),
              failure=True)),
  )

  yield api.test(
      'flaky_tests',
      base({
          'gl_tests': ['Test.One', 'Test.Two', 'Test.Three']
      }, 'win', 'Win7 Tests (1)'),
      api.chromium_tests.read_source_side_spec(
          'chromium.win', {
              'Win7 Tests (1)': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r0.'),
      api.override_step_data(
          'test r0.gl_tests (r0)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  failed_test_names=['Test.One'],
                  passed_test_names=['Test.Two']),
              failure=True)),
      api.chromium_tests.read_source_side_spec(
          'chromium.win', {
              'Win7 Tests (1)': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r1.'),
      api.override_step_data(
          'test r1.gl_tests (r1)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  failed_test_names=['Test.One', 'Test.Two'],
                  passed_test_names=['Test.Three']),
              failure=True)),
  )

  yield api.test(
      'use_abbreviated_revision_in_step_name',
      base({
          'gl_tests': ['Test.One']
      },
           'mac',
           'Mac10.13 Tests',
           use_analyze=False,
           good_revision='1234567890abcdefg',
           bad_revision='gfedcba0987654321',
           test_on_good_revision=False),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test gfedcba.'),
      api.override_step_data('git commits in range',
                             api.raw_io.stream_output('gfedcba0987654321')),
      api.override_step_data(
          'test gfedcba.gl_tests (gfedcba)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  failed_test_names=['Test.One']),
              failure=True)),
  )

  yield api.test(
      'remove_culprits_for_flaky_failures',
      base({
          'gl_tests': ['Test.One', 'Test.Two']
      },
           'mac',
           'Mac10.13 Tests',
           use_analyze=False,
           good_revision='r0',
           bad_revision='r6',
           suspected_revisions=['r4']),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r3.'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r4.'),
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output('\n'.join(
              'r%d' % i for i in reversed(range(1, 7))))),
      api.override_step_data(
          'test r3.gl_tests (r3)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  passed_test_names=['Test.One', 'Test.Two']),
              failure=True)),
      api.override_step_data(
          'test r4.gl_tests (r4)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  flaky_test_names=['Test.One'],
                  failed_test_names=['Test.Two']),
              failure=True)),
  )

  yield api.test(
      'blink_web_tests',
      base({
          'blink_web_tests': [
              'fast/Test/One.html', 'fast/Test/Two.html', 'dummy/Three.js'
          ]
      }, 'mac', 'Mac10.13 Tests'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'blink_web_tests',
                      'name': 'blink_web_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 1,
                      },
                  },],
              },
          },
          step_prefix='test r0.'),
      api.override_step_data(
          'test r0.blink_web_tests (r0)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_isolated_script_output(
                  failed_test_names=['fast/Test/One.html'],
                  passed_test_names=['fast/Test/Two.html'],
                  path_delimiter='/'),
              failure=True)),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'blink_web_tests',
                      'name': 'blink_web_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 1,
                      },
                  },],
              },
          },
          step_prefix='test r1.'),
      api.override_step_data(
          'test r1.blink_web_tests (r1)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_isolated_script_output(
                  failed_test_names=[
                      'fast/Test/One.html', 'fast/Test/Two.html'
                  ],
                  passed_test_names=['dummy/Three.js'],
                  path_delimiter='/'),
              failure=True)),
  )

  yield api.test(
      'builder_as_tester',
      base({
          'services_unittests': ['Test.One']
      }, 'linux', 'linux-ozone-rel'),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'linux-ozone-rel': {
                  'gtest_tests': [{
                      'test': 'services_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r1.'),
      api.override_step_data(
          'test r1.services_unittests (r1)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  passed_test_names=['Test.One']))),
  )

  yield api.test(
      'gtest_task_failed',
      base({
          'services_unittests': ['Test.One']
      }, 'linux', 'linux-ozone-rel'),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'linux-ozone-rel': {
                  'gtest_tests': [{
                      'test': 'services_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r1.'),
      api.override_step_data(
          'test r1.services_unittests (r1)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(None, 255))),
      api.post_process(
          verify_report_fields,
          {'result': {
              'r1': {
                  'services_unittests': {
                      'pass_fail_counts': {}
                  }
              }
          }}),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'isolated_script_test_task_failed',
      base({
          'blink_web_tests': [
              'fast/Test/One.html', 'fast/Test/Two.html', 'dummy/Three.js'
          ]
      }, 'mac', 'Mac10.13 Tests'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'blink_web_tests',
                      'name': 'blink_web_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 1,
                      },
                  },],
              },
          },
          step_prefix='test r1.'),
      api.override_step_data(
          'test r1.blink_web_tests (r1)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.m.json.output(None, 255), failure=True)),
      api.post_process(
          verify_report_fields,
          {'result': {
              'r1': {
                  'blink_web_tests': {
                      'pass_fail_counts': {}
                  }
              }
          }}),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'first_revision_compile_failure',
      base({
          'gl_tests': ['Test.One']
      },
           'mac',
           'Mac10.13 Tests',
           use_analyze=False,
           good_revision='r0',
           bad_revision='r6',
           suspected_revisions=['r3', 'r6']),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r5.'),
      api.override_step_data(
          'git commits in range',
          api.raw_io.stream_output('\n'.join(
              'r%d' % i for i in reversed(range(1, 7))))),
      api.step_data('test r5.compile', retcode=1),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'second_revision_compile_failure',
      base({
          'gl_tests': ['Test.One']
      }, 'mac', 'Mac10.13 Tests'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r1.'),
      api.step_data('test r1.compile', retcode=1),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'third_revision_compile_failure',
      base({
          'gl_tests': ['Test.One', 'Test.Two', 'Test.Three']
      }, 'win', 'Win7 Tests (1)'),
      api.chromium_tests.read_source_side_spec(
          'chromium.win', {
              'Win7 Tests (1)': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r0.'),
      api.chromium_tests.read_source_side_spec(
          'chromium.win', {
              'Win7 Tests (1)': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r1.'),
      api.override_step_data(
          'test r1.gl_tests (r1)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  failed_test_names=['Test.One', 'Test.Two'],
                  passed_test_names=['Test.Three']),
              failure=True)),
      api.step_data('test r0.compile', retcode=1),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )
