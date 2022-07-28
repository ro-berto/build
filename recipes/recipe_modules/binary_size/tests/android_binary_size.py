# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine import recipe_api

from PB.recipe_modules.build.binary_size import properties as properties_pb
from RECIPE_MODULES.build.binary_size import constants

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'binary_size',
    'recipe_engine/json',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/time',
]


def RunSteps(api):
  return api.binary_size.android_binary_size(
      chromium_config='chromium',
      chromium_apply_configs=['mb'],
      gclient_config='chromium',
      gclient_apply_configs=['android'])


def GenTests(api):

  def override_analyze(no_changes=False):
    """Overrides analyze step data so that targets get compiled."""
    return api.override_step_data(
        'analyze',
        api.json.output({
            'status':
                'Found dependency',
            'compile_targets':
                constants.DEFAULT_ANALYZE_TARGETS,
            'test_targets': []
                            if no_changes else constants.DEFAULT_COMPILE_TARGETS
        }))

  def override_expectation_to_fail(with_patch=True, use_alternative=False):
    suffix = ' (with patch)' if with_patch else ' (without patch)'
    failed_messages = ['Failure Message A']
    if use_alternative:
      failed_messages += ['Failure Message B']
    return api.step_data(
        'Run Expectations Script' + suffix,
        api.json.output({
            'success': False,
            'failed_messages': failed_messages,
        }))

  def has_binary_size_property(check, steps):
    check(steps['analyze'].output_properties['binary_size_plugin'] is not None)

  yield api.test('noop_because_of_analyze',
                 api.binary_size.build(override_commit_log=True),
                 api.post_check(has_binary_size_property),
                 api.post_process(post_process.MustRun, 'analyze'),
                 api.post_process(post_process.DoesNotRunRE, r'.*compile'),
                 api.post_process(post_process.DropExpectation))
  yield api.test('compile_failure',
                 api.binary_size.build(override_commit_log=True),
                 override_analyze(),
                 api.override_step_data('compile (with patch)', retcode=1),
                 api.post_process(post_process.StatusFailure),
                 api.post_process(post_process.DropExpectation))
  yield api.test(
      'patch_fixes_build', api.binary_size.build(), override_analyze(),
      api.override_step_data('compile (without patch)', retcode=1),
      api.time.seed(constants.TEST_TIME + 7230),
      api.post_process(post_process.MustRun,
                       constants.PATCH_FIXED_BUILD_STEP_NAME),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation))

  def has_expected_supersize_link(check,
                                  steps,
                                  bucket=constants.NDJSON_GS_BUCKET):
    expected_url = 'https://foo.com/{}'.format(
        constants.ARCHIVED_URL_FMT.format(
            bucket=bucket,
            dest='{}/{}/{}/result.ndjson'.format(constants.TEST_BUILDER,
                                                 constants.TEST_TIME_FMT,
                                                 constants.TEST_BUILDNUMBER)))
    check(steps[constants.RESULTS_STEP_NAME].links['Supersize HTML Diff'] ==
          expected_url)

  def has_expected_binary_size_url(check,
                                   steps,
                                   bucket=constants.NDJSON_GS_BUCKET):
    expected_url = constants.ARCHIVED_URL_FMT.format(
        bucket=bucket,
        dest='{}/{}/{}/result.txt'.format(constants.TEST_BUILDER,
                                          constants.TEST_TIME_FMT,
                                          constants.TEST_BUILDNUMBER))
    results_step = steps[constants.RESULTS_STEP_NAME]
    binary_size_prop = results_step.output_properties['binary_size_plugin']
    actual_url = binary_size_prop['extras'][-1]['url']
    check(actual_url == expected_url)

  def final_step_is_not_nested(check, steps):
    # This test is to make sure that binary_size._synthesize_log_link logs
    # linking logic is correct. If this fails, please make sure to fix the
    # format string in _synthesize_log_link alongside this test.

    # checks that step name constant is not already nested
    check('.' not in constants.RESULTS_STEP_NAME)
    # checks that step name actually exists (i.e. not nested in another step).
    check(constants.RESULTS_STEP_NAME in steps)
    # checks that first character of step name is not illegal.
    check(constants.RESULTS_STEP_NAME[0].isalnum())
    # checks that this is actually the final/relevant step.
    check('binary_size_plugin' in (
        steps[constants.RESULTS_STEP_NAME].output_properties))

  yield api.test(
      'normal_build',
      api.binary_size.build('normal_build', override_commit_log=True),
      override_analyze(), api.post_check(has_expected_supersize_link),
      api.post_check(has_expected_binary_size_url),
      api.post_check(final_step_is_not_nested),
      api.post_process(post_process.StepSuccess, constants.RESULTS_STEP_NAME),
      api.post_process(post_process.StatusSuccess))

  yield api.test(
      'normal_nondefault_targets',
      api.binary_size.build('nondefault_targets', override_commit_log=True),
      api.binary_size.properties(
          analyze_targets=['//foo:bar_binary'], compile_targets=['bar_binary']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'normal_significant_binary_package_restructure',
      override_analyze(),
      api.binary_size.build('normal build + significant package restructure'),
      api.binary_size.on_significant_binary_package_restructure(),
      api.post_process(post_process.StatusSuccess),
  )

  yield api.test(
      'unexpected_increase', api.binary_size.build(override_commit_log=True),
      override_analyze(),
      api.override_step_data(
          constants.RESULT_JSON_STEP_NAME,
          api.json.output({
              'status_code': 1,
              'summary': '\n!summary!',
              'archive_filenames': [],
              'links': [],
          })),
      api.post_process(post_process.StepFailure, constants.RESULTS_STEP_NAME),
      api.post_process(post_process.StatusFailure))

  def has_failed_expectations(check, steps):
    check(steps[constants.EXPECTATIONS_STEP_NAME].logs['failed expectations'] is
          not None)

  yield api.test(
      'expectations_file_warning',
      api.binary_size.build(override_commit_log=True), override_analyze(),
      api.override_step_data('bot_update', retcode=1),
      override_expectation_to_fail(with_patch=True),
      override_expectation_to_fail(with_patch=False),
      api.post_process(post_process.StepWarning,
                       constants.EXPECTATIONS_STEP_NAME),
      api.post_check(has_failed_expectations),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation))
  yield api.test(
      'expectations_file_failure',
      api.binary_size.build(override_commit_log=True), override_analyze(),
      override_expectation_to_fail(with_patch=True),
      api.post_process(post_process.StepFailure,
                       constants.EXPECTATIONS_STEP_NAME),
      api.post_check(has_failed_expectations),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation))
  yield api.test(
      'expectations_file_failure_with_note',
      api.binary_size.build(override_commit_log=True), override_analyze(),
      api.override_step_data('bot_update', retcode=1),
      override_expectation_to_fail(with_patch=True),
      override_expectation_to_fail(with_patch=False, use_alternative=True),
      api.post_process(post_process.StepFailure,
                       constants.EXPECTATIONS_STEP_NAME),
      api.post_check(has_failed_expectations),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation))
  yield api.test(
      'expectations_file_failure_skipped_due_to_footer',
      api.binary_size.build(
          override_commit_log=True,
          extra_footers={
              constants.SKIP_EXPECTATIONS_FOOTER_KEY: "Reasons to skip"
          }), override_analyze(),
      api.override_step_data('bot_update', retcode=1),
      override_expectation_to_fail(with_patch=True),
      override_expectation_to_fail(with_patch=False, use_alternative=True),
      api.post_process(post_process.StepFailure,
                       constants.EXPECTATIONS_STEP_NAME),
      api.post_check(has_failed_expectations),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation))
  yield api.test(
      'clear_expectation_files_ignores_failure',
      api.binary_size.build(override_commit_log=True), override_analyze(),
      api.override_step_data('Clear Expectation Files', retcode=1),
      api.post_process(post_process.StepSuccess, 'Clear Expectation Files'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation))
  yield api.test(
      'pass_because_of_size_footer',
      api.binary_size.build(android_size_footer=True, override_commit_log=True),
      override_analyze(),
      api.override_step_data(
          constants.RESULT_JSON_STEP_NAME,
          api.json.output({
              'status_code': 1,
              'summary': '\n!summary!',
              'archive_filenames': [],
              'links': [],
          })),
      api.post_process(post_process.StepSuccess, constants.RESULTS_STEP_NAME),
      api.post_process(post_process.DropExpectation))
  yield api.test(
      'fail_because_of_wrong_size_footer',
      api.binary_size.build(fuchsia_size_footer=True, override_commit_log=True),
      override_analyze(),
      api.override_step_data(
          constants.RESULT_JSON_STEP_NAME,
          api.json.output({
              'status_code': 1,
              'summary': '\n!summary!',
              'archive_filenames': [],
              'links': [],
          })),
      api.post_process(post_process.StepFailure, constants.RESULTS_STEP_NAME),
      api.post_process(post_process.DropExpectation))
  yield api.test(
      'pass_because_of_revert',
      api.binary_size.build(
          commit_message='Revert some change', override_commit_log=True),
      override_analyze(),
      api.override_step_data(
          constants.RESULT_JSON_STEP_NAME,
          api.json.output({
              'status_code': 1,
              'summary': '\n!summary!',
              'archive_filenames': [],
              'links': [],
          })),
      api.post_process(post_process.StepSuccess, constants.RESULTS_STEP_NAME),
      api.post_process(post_process.DropExpectation))

  yield api.test(
      'nondefault_results_bucket',
      api.binary_size.build(override_commit_log=True),
      api.binary_size.properties(results_bucket='fake-results-bucket'),
      override_analyze(),
      api.post_check(has_expected_supersize_link, bucket='fake-results-bucket'),
      api.post_check(
          has_expected_binary_size_url, bucket='fake-results-bucket'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation))

  yield api.test(
      'valid_latest_file', api.binary_size.build(override_commit_log=True),
      override_analyze(),
      api.post_process(post_process.MustRun, 'gsutil Downloading zip'),
      api.post_process(post_process.DoesNotRun, 'compile (without patch)'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation))

  yield api.test(
      'valid_latest_file_merge_conflict',
      api.binary_size.build(override_commit_log=True), override_analyze(),
      api.override_step_data('bot_update', retcode=1),
      api.post_process(post_process.MustRun, 'bot_update (2)'),
      api.post_process(post_process.DoesNotRun, 'gsutil Downloading zip'),
      api.post_process(post_process.MustRun, 'compile (without patch)'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation))

  yield api.test(
      'invalid_latest_file', api.binary_size.build(), override_analyze(),
      api.time.seed(constants.TEST_TIME + 7230),
      api.post_process(post_process.DoesNotRun, 'gsutil Downloading zip'),
      api.post_process(post_process.MustRun, 'compile (without patch)'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation))

  yield api.test(
      'patch_parent_rev_too_new',
      api.binary_size.build(
          recent_upload_cp=12345,
          patch_parent_cp=12350,
          override_commit_log=True), override_analyze(),
      api.post_process(post_process.DoesNotRun, 'gsutil Downloading zip'),
      api.post_process(post_process.MustRun, 'compile (without patch)'),
      api.post_check(has_expected_supersize_link),
      api.post_check(has_expected_binary_size_url),
      api.post_check(final_step_is_not_nested),
      api.post_process(post_process.StepSuccess, constants.RESULTS_STEP_NAME),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation))

  yield api.test(
      'patch_parent_no_cp',
      api.binary_size.build(
          recent_upload_cp=12345,
          patch_parent_cp=None,
          override_commit_log=True), override_analyze(),
      api.post_process(post_process.DoesNotRun, 'gsutil Downloading zip'),
      api.post_process(post_process.MustRun, 'compile (without patch)'),
      api.post_check(has_expected_supersize_link),
      api.post_check(has_expected_binary_size_url),
      api.post_check(final_step_is_not_nested),
      api.post_process(post_process.StepSuccess, constants.RESULTS_STEP_NAME),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation))
