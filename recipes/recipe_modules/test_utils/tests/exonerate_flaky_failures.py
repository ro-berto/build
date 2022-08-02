# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'recipe_engine/assertions',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'chromium',
    'chromium_tests',
    'test_utils',
]

from recipe_engine.recipe_api import Property
from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import steps

PROPERTIES = {
    # This property is a dictionary that specifies the expectations of the
    # labeled known flakes of the mocked tests, and the format is from a test
    # name to a list of tests.
    'known_flakes_expectations': Property(default={}),
    # This property is a dictionary that specifies the expectations of the
    # labeled known flakes of the mocked tests, and the format is from a test
    # name to a list of tests.
    'known_weetbix_flakes_expectations': Property(default={}),

    # This property is a boolean that indicates whether to create a mocked test
    # that has failed tests to test that if there are no test failures, a
    # request should NOT be sent to the service because it's unnecessary.
    'exclude_failed_test': Property(default=False),

    # This property is a boolean that indicates whether to create a mocked test
    # that has a massive amount of failures to test that a request should NOT be
    # sent to the service to avoid overloading it.
    'has_too_many_failures': Property(default=False),

    # This property indicates how many failed_test suites to create
    'failed_test_count': Property(default=1),

    # This property is a list of test suite names to expect to be returned
    # from run_test()
    # If this is empty, the run_test() return value will not be checked.
    'expected_failed_test_suites': Property(default=[]),

    # This property indicates whether the failed tests should also fail on retry
    'fails_retries': Property(default=False),
}


def RunSteps(api, known_flakes_expectations, known_weetbix_flakes_expectations,
             exclude_failed_test, has_too_many_failures, failed_test_count,
             expected_failed_test_suites, fails_retries):
  test_specs = [
      steps.MockTestSpec.create(name='succeeded_test'),
      steps.MockTestSpec.create(
          name='invalid_test', runs_on_swarming=True, has_valid_results=False),
  ]

  if not exclude_failed_test:
    test_suite_name = 'failed_test'
    for i in range(failed_test_count):
      if i != 0:
        test_suite_name += '_{}'.format(i)
      per_suffix_failures = {'with patch': ['testA', 'testB']}
      if fails_retries:
        per_suffix_failures['retry shards with patch'] = ['testA', 'testB']
      test_specs.append(
          steps.MockTestSpec.create(
              name=test_suite_name,
              runs_on_swarming=True,
              per_suffix_failures=per_suffix_failures,
              invocation_names=['invocations/whatever'],
          ))

  if has_too_many_failures:
    test_specs.append(
        steps.MockTestSpec.create(
            name='too_many_failures',
            runs_on_swarming=True,
            per_suffix_failures={
                'with patch': ['test%d' % i for i in range(1000)]
            }))
  tests = [s.get_test(api.chromium_tests) for s in test_specs]

  invalid_suites, failed_and_invalid_suites = api.test_utils.run_tests(
      tests, 'with patch', retry_failed_shards=True, retry_invalid_shards=True)

  if expected_failed_test_suites:
    failed_and_invalid_suite_names = set(
        [t.name for t in failed_and_invalid_suites])
    invalid_suite_names = set([t.name for t in invalid_suites])
    failed_test_names = failed_and_invalid_suite_names - invalid_suite_names
    api.assertions.assertSetEqual(
        set(expected_failed_test_suites), failed_test_names)

  for t in tests:
    assert t.known_flaky_failures == set(
        known_flakes_expectations.get(t.name, []))
    assert t.known_weetbix_flaky_failures == set(
        known_weetbix_flakes_expectations.get(t.name, []))


def GenTests(api):

  def construct_recent_verdicts(expected_count, unexpected_count):
    verdicts = []
    for i in range(expected_count):
      verdicts.append({
          'ingested_invocation_id': 'invocation_id_' + str(i),
          'hasUnexpectedRuns': False,
      })
    for i in range(unexpected_count):
      verdicts.append({
          'ingested_invocation_id': 'invocation_id_' + str(i * 10),
          'hasUnexpectedRuns': True,
      })
    return verdicts

  def generate_analysis(test_name,
                        is_flaky,
                        suite_name='failed_test',
                        expected_count=10,
                        unexpected_count=0):
    return {
        'testId':
            'ninja://{}/{}'.format(suite_name, test_name),
        'variantHash':
            'fake_variant_hash',
        'intervalStats': [
            {
                'intervalAge': 1,
                'totalRunExpectedVerdicts': 300,
                'totalRunUnexpectedVerdicts': 1,
                'totalRunFlakyVerdicts': 10 if is_flaky else 0,
            },
            {
                'intervalAge': 2,
                'totalRunExpectedVerdicts': 300,
                'totalRunFlakyVerdicts': 10 if is_flaky else 0,
            },
        ],
        'recentVerdicts':
            construct_recent_verdicts(
                expected_count=expected_count,
                unexpected_count=unexpected_count,
            )
    }

  yield api.test(
      'immune to infra failure of querying flaky failures',
      api.chromium.generic_build(
          builder_group='g',
          builder='b',
          experiments=['enable_weetbix_queries']),
      api.properties(**{
          '$build/test_utils': {
              'should_exonerate_flaky_failures': True,
          },
      }),
      api.step_data('query known flaky failures on CQ', retcode=1),
      api.override_step_data(
          'query weetbix for failure rates.rpc call', retcode=1),
      api.post_process(post_process.MustRun,
                       'error querying weetbix for failure rates'),
      api.post_process(post_process.MustRun,
                       'query known flaky failures on CQ'),
      api.post_process(post_process.StepTextContains,
                       'query known flaky failures on CQ',
                       ['Failed to get known flakes']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'immune to ill-formed response',
      api.chromium.generic_build(
          builder_group='g',
          builder='b',
          experiments=['enable_weetbix_queries']),
      api.properties(**{
          '$build/test_utils': {
              'should_exonerate_flaky_failures': True,
          },
      }),
      api.step_data(
          'query weetbix for failure rates.rpc call',
          stdout=api.raw_io.output_text(api.json.dumps({'testVariants': []})),
      ),
      api.step_data(
          'query known flaky failures on CQ',
          api.json.output({'step_ui_name': 'browser_tests (with patch)'})),
      api.post_process(post_process.StepTextContains,
                       'query known flaky failures on CQ',
                       ['Response is ill-formed']),
      api.post_process(post_process.MustRun,
                       'error querying weetbix for failure rates'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'immune to another ill-formed response',
      api.chromium.generic_build(builder_group='g', builder='b'),
      api.properties(**{
          '$build/test_utils': {
              'should_exonerate_flaky_failures': True,
          },
      }),
      api.step_data(
          'query known flaky failures on CQ',
          api.json.output(
              {'flakes': [{
                  'step_ui_name': 'browser_tests (with patch)'
              }]})),
      api.post_process(post_process.StepTextContains,
                       'query known flaky failures on CQ',
                       ['Response is ill-formed']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'empty response',
      api.chromium.generic_build(
          builder_group='g',
          builder='b',
          experiments=['enable_weetbix_queries']),
      api.properties(**{
          '$build/test_utils': {
              'should_exonerate_flaky_failures': True,
          },
      }),
      api.step_data(
          'query weetbix for failure rates.rpc call',
          stdout=api.raw_io.output_text(api.json.dumps({})),
      ),
      api.post_process(post_process.MustRun,
                       'error querying weetbix for failure rates'),
      api.step_data('query known flaky failures on CQ', api.json.output({})),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no failed tests',
      api.chromium.generic_build(
          builder_group='g',
          builder='b',
          experiments=['enable_weetbix_queries']),
      api.properties(
          exclude_failed_test=True,
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.post_process(post_process.DoesNotRun,
                       'query known flaky failures on CQ'),
      api.post_process(post_process.DoesNotRun,
                       'query weetbix for failure rates'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no tests are marked as known flaky or recently failing',
      api.chromium.generic_build(
          builder_group='g',
          builder='b',
          experiments=['enable_weetbix_queries']),
      api.override_step_data(
          'failed_test results',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  'failed_test', failing_tests=['testA', 'testB']))),
      api.properties(
          known_flakes_expectations={},
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.step_data('query known flaky failures on CQ', api.json.output([])),
      api.step_data(
          'query weetbix for failure rates.rpc call',
          stdout=api.raw_io.output_text(
              api.json.dumps({
                  'testVariants': [
                      generate_analysis(
                          'testA', False, expected_count=10,
                          unexpected_count=0),
                      generate_analysis(
                          'testB', False, expected_count=10,
                          unexpected_count=0),
                  ]
              })),
      ),
      api.post_process(post_process.MustRun,
                       'query known flaky failures on CQ'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  def CheckStepInput(check, step_odict, step_name, test_name):
    step = step_odict[step_name]
    check(test_name in step.stdin)

  yield api.test(
      'part of the tests are marked as known flaky',
      api.chromium.generic_build(
          builder_group='g',
          builder='b',
          experiments=['enable_weetbix_queries']),
      api.properties(
          known_flakes_expectations={
              'failed_test': ['testA'],
          },
          known_weetbix_flakes_expectations={
              'failed_test': ['testA'],
          },
          override_failed_test_names=['testA'],
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.override_step_data(
          'failed_test results',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  'failed_test', failing_tests=['testA']))),
      api.step_data(
          'query weetbix for failure rates.rpc call',
          stdout=api.raw_io.output_text(
              api.json.dumps(
                  {'testVariants': [generate_analysis('testA', True),]})),
      ),
      api.step_data(
          'query known flaky failures on CQ',
          api.json.output({
              'flakes': [{
                  'test': {
                      'step_ui_name': 'failed_test (with patch)',
                      'test_name': 'testA',
                  },
                  'affected_gerrit_changes': ['123', '234'],
                  'monorail_issue': '999',
              }]
          })),
      api.post_process(post_process.MustRun,
                       'query known flaky failures on CQ'),
      api.post_process(post_process.MustRun,
                       'exonerate unrelated test failures'),
      api.post_process(CheckStepInput, 'exonerate unrelated test failures',
                       'testA'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'all of the tests are marked as known flaky',
      api.chromium.generic_build(
          builder_group='g',
          builder='b',
          experiments=['enable_weetbix_queries']),
      api.override_step_data(
          'failed_test results',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  'failed_test', failing_tests=['testA', 'testB']))),
      api.properties(
          known_flakes_expectations={
              'failed_test': ['testA', 'testB'],
          },
          known_weetbix_flakes_expectations={
              'failed_test': ['testA', 'testB'],
          },
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.step_data(
          'query known flaky failures on CQ',
          api.json.output({
              'flakes': [
                  {
                      'test': {
                          'step_ui_name': 'failed_test (with patch)',
                          'test_name': 'testA',
                      },
                      'affected_gerrit_changes': ['123', '234'],
                      'monorail_issue': '999',
                  },
                  {
                      'test': {
                          'step_ui_name': 'failed_test (with patch)',
                          'test_name': 'testB',
                      },
                      'affected_gerrit_changes': ['567', '678'],
                      'monorail_issue': '998',
                  },
              ]
          })),
      api.step_data(
          'query weetbix for failure rates.rpc call',
          stdout=api.raw_io.output_text(
              api.json.dumps({
                  'testVariants': [
                      generate_analysis('testA', True),
                      generate_analysis('testB', True),
                  ]
              })),
      ),
      api.post_process(post_process.MustRun,
                       'query known flaky failures on CQ'),
      api.post_process(post_process.MustRun,
                       'exonerate unrelated test failures'),
      api.post_process(CheckStepInput, 'exonerate unrelated test failures',
                       'testA'),
      api.post_process(CheckStepInput, 'exonerate unrelated test failures',
                       'testB'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'tests are deterministically failing',
      api.chromium.generic_build(
          builder_group='g',
          builder='b',
          experiments=['enable_weetbix_queries'],
      ),
      api.override_step_data(
          'failed_test results',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  'failed_test', failing_tests=['testA']))),
      api.properties(
          known_flakes_expectations={
              'failed_test': ['testA'],
          },
          known_weetbix_flakes_expectations={
              'failed_test': ['testA'],
          },
          override_failed_test_names=['testA'],
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.step_data(
          'query known flaky failures on CQ',
          api.json.output({
              'flakes': [{
                  'test': {
                      'step_ui_name': 'failed_test (with patch)',
                      'test_name': 'testA',
                  },
                  'affected_gerrit_changes': ['123', '234'],
                  'monorail_issue': '999',
              }],
          })),
      api.step_data(
          'query weetbix for failure rates.rpc call',
          stdout=api.raw_io.output_text(
              api.json.dumps({
                  'testVariants': [
                      generate_analysis(
                          'testA',
                          is_flaky=False,
                          expected_count=1,
                          unexpected_count=9)
                  ]
              })),
      ),
      api.post_process(post_process.PropertiesContain, 'weetbix_info'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'skip querying if there are too many failures',
      api.chromium.generic_build(
          builder_group='g',
          builder='b',
          experiments=['enable_weetbix_queries']),
      api.properties(
          exclude_failed_test=True,
          has_too_many_failures=True,
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.post_process(post_process.DoesNotRun,
                       'query weetbix for failure rates'),
      api.post_process(post_process.DoesNotRun,
                       'query known flaky failures on CQ'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  # The difference between this test and the immediate above one is that this
  # test doesn't exclude the test suite with limited number of failures, and
  # this test tests that even though there are tests with too many failures, the
  # recipe should still query known flaky failures for other test suites with
  # limited number of failures.
  yield api.test(
      'keep querying if at least one test suite has limited failures',
      api.chromium.generic_build(
          builder_group='g',
          builder='b',
          experiments=['enable_weetbix_queries']),
      api.override_step_data(
          'failed_test results',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  'failed_test', failing_tests=['testA', 'testB']))),
      api.properties(
          has_too_many_failures=True,
          known_weetbix_flakes_expectations={
              'failed_test': ['testA', 'testB'],
          },
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.step_data(
          'query weetbix for failure rates.rpc call',
          stdout=api.raw_io.output_text(
              api.json.dumps({
                  'testVariants': [
                      generate_analysis('testA', True),
                      generate_analysis('testB', True),
                  ]
              })),
      ),
      api.post_process(post_process.LogContains,
                       'query known flaky failures on CQ', 'input',
                       ['failed_test (with patch)']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_findit_exonerations',
      api.chromium.generic_build(
          builder_group='g',
          builder='b',
          experiments=['enable_weetbix_queries', 'retry_findit_exonerations']),
      api.override_step_data(
          'failed_test results',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  'failed_test', failing_tests=['testA', 'testB']))),
      api.override_step_data(
          'failed_test_1 results',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  'failed_test_1', failing_tests=['testA', 'testB']))),
      api.override_step_data(
          'failed_test results (2)',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  'failed_test', failing_tests=['testA', 'testB']))),
      api.override_step_data(
          'failed_test_1 results (2)',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  'failed_test_1', failing_tests=['testA', 'testB']))),
      api.properties(
          known_flakes_expectations={
              'failed_test_1': ['testA', 'testB'],
          },
          known_weetbix_flakes_expectations={
              'failed_test_1': ['testA', 'testB'],
          },
          failed_test_count=2,
          expected_failed_test_suites=['failed_test'],
          fails_retries=True,
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.step_data(
          'query known flaky failures on CQ',
          api.json.output({
              'flakes': [
                  {
                      'test': {
                          'step_ui_name': 'failed_test_1 (with patch)',
                          'test_name': 'testA',
                      },
                      'affected_gerrit_changes': ['123', '234'],
                      'monorail_issue': '999',
                  },
                  {
                      'test': {
                          'step_ui_name': 'failed_test_1 (with patch)',
                          'test_name': 'testB',
                      },
                      'affected_gerrit_changes': ['123', '234'],
                      'monorail_issue': '999',
                  },
              ]
          })),
      api.step_data(
          'query weetbix for failure rates.rpc call',
          stdout=api.raw_io.output_text(
              api.json.dumps({
                  'testVariants': [
                      generate_analysis('testA', False),
                      generate_analysis('testB', False),
                      generate_analysis(
                          'testA', True, suite_name='failed_test_1'),
                      generate_analysis(
                          'testB', True, suite_name='failed_test_1'),
                  ]
              })),
      ),
      api.post_process(post_process.MustRun,
                       'query known flaky failures on CQ'),
      api.post_process(CheckStepInput, 'exonerate unrelated test failures',
                       'failed_test_1_hash'),
      api.post_process(post_process.MustRun,
                       'failed_test (retry shards with patch)'),
      api.post_process(post_process.MustRun,
                       'failed_test_1 (retry shards with patch)'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.PropertiesContain,
                       'retried_findit_exonerations'),
      api.post_process(post_process.DropExpectation),
  )
