# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine import recipe_api

from PB.recipe_modules.build.binary_size import properties as properties_pb
from RECIPE_MODULES.build.binary_size import constants

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

  def override_expectation():
    return api.step_data(
        'Run Expectations Script',
        api.json.output({
            'success': True,
            'failed_messages': []
        }))

  def has_binary_size_property(check, steps):
    check(steps['analyze'].output_properties['binary_size_plugin'] is not None)

  yield api.test('noop_because_of_analyze', api.binary_size.build(),
                 api.post_check(has_binary_size_property),
                 api.post_process(post_process.MustRun, 'analyze'),
                 api.post_process(post_process.DoesNotRunRE, r'.*build'),
                 api.post_process(post_process.DropExpectation))
  yield api.test('compile_failure', api.binary_size.build(), override_analyze(),
                 api.override_step_data('compile (with patch)', retcode=1),
                 api.post_process(post_process.StatusFailure),
                 api.post_process(post_process.DropExpectation))
  yield api.test(
      'patch_fixes_build', api.binary_size.build(), override_analyze(),
      api.override_step_data('compile (without patch)', retcode=1),
      api.post_process(post_process.MustRun,
                       constants.PATCH_FIXED_BUILD_STEP_NAME),
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
    check(steps.has_key(constants.RESULTS_STEP_NAME))
    # checks that first character of step name is not illegal.
    check(constants.RESULTS_STEP_NAME[0].isalnum())
    # checks that this is actually the final/relevant step.
    check(steps[constants.RESULTS_STEP_NAME].output_properties.has_key(
        'binary_size_plugin'))

  yield api.test(
      'normal_build', api.binary_size.build('normal_build'), override_analyze(),
      override_expectation(), api.post_check(has_expected_supersize_link),
      api.post_check(has_expected_binary_size_url),
      api.post_check(final_step_is_not_nested),
      api.post_process(post_process.StepSuccess, constants.RESULTS_STEP_NAME),
      api.post_process(post_process.StatusSuccess))

  nondefault_properties = properties_pb.InputProperties(
      analyze_targets=['//foo:bar_binary'], compile_targets=['bar_binary'])
  yield api.test(
      'normal_nondefault_targets',
      api.binary_size.build('nondefault_targets'),
      api.properties(**{'$build/binary_size': nondefault_properties}),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'unexpected_increase', api.binary_size.build(), override_analyze(),
      override_expectation(),
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
      'expectations_file_failure',
      api.binary_size.build('expectations_file_failure'), override_analyze(),
      api.override_step_data(
          'Run Expectations Script',
          api.json.output({
              'success':
                  False,
              'failed_messages': [
                  'ProGuard flag expectations file needs updating. For details '
                  'see:\nhttps://chromium.googlesource.com/chromium/src/+/HEAD/'
                  'chrome/android/java/README.md\n',
              ]
          })),
      api.post_process(post_process.StepFailure,
                       constants.EXPECTATIONS_STEP_NAME),
      api.post_check(has_failed_expectations),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation))
  yield api.test(
      'clear_expectation_files_ignores_failure', api.binary_size.build(),
      override_analyze(), override_expectation(),
      api.override_step_data('Clear Expectation Files', retcode=1),
      api.post_process(post_process.StepSuccess, 'Clear Expectation Files'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation))
  yield api.test(
      'pass_because_of_size_footer', api.binary_size.build(size_footer=True),
      override_analyze(), override_expectation(),
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
      'pass_because_of_revert',
      api.binary_size.build(commit_message='Revert some change'),
      override_analyze(), override_expectation(),
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
      'nondefault_results_bucket', api.binary_size.build(),
      api.binary_size.properties(results_bucket='fake-results-bucket'),
      override_analyze(), override_expectation(),
      api.post_check(has_expected_supersize_link, bucket='fake-results-bucket'),
      api.post_check(
          has_expected_binary_size_url, bucket='fake-results-bucket'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation))
