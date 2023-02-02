# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'recipe_engine/assertions',
    'recipe_engine/json',
    'recipe_engine/luci_analysis',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'recipe_engine/time',
    'chromium',
    'chromium_tests',
    'test_utils',
    'weetbix',
]

from recipe_engine.recipe_api import Property
from recipe_engine import post_process
from google.protobuf import json_format
from google.protobuf import timestamp_pb2

from RECIPE_MODULES.build.chromium_tests import steps

PROPERTIES = {
    # This property is a dictionary that specifies the expectations of the
    # labeled known flakes of the mocked tests, and the format is from a test
    # name to a list of tests.
    'known_luci_analysis_flakes_expectations': Property(default={}),
    'weak_flaky_failures': Property(default={}),

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

    # This property indicates whether all the mock tests will be valid
    'all_valid': Property(default=False),
}


def RunSteps(api, known_luci_analysis_flakes_expectations, weak_flaky_failures,
             exclude_failed_test, has_too_many_failures, all_valid):
  test_specs = [
      steps.MockTestSpec.create(name='succeeded_test'),
      steps.MockTestSpec.create(
          name='invalid_test',
          runs_on_swarming=True,
          has_valid_results=all_valid),
  ]

  if not exclude_failed_test:
    test_suite_name = 'failed_test'
    per_suffix_failures = {'with patch': ['testA', 'testB']}
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

  api.test_utils.run_tests(
      tests, 'with patch', retry_failed_shards=True, retry_invalid_shards=True)

  for t in tests:
    api.assertions.assertEqual(
        t.known_luci_analysis_flaky_failures,
        set(known_luci_analysis_flakes_expectations.get(t.name, [])))
    api.assertions.assertEqual(t.weak_luci_analysis_flaky_failures,
                               set(weak_flaky_failures.get(t.name, [])))


def GenTests(api):

  yield api.test(
      'immune to infra failure of querying flaky failures',
      api.chromium.generic_build(
          builder_group='fake-group',
          builder='fake-builder',
          experiments=['enable_weetbix_queries']),
      api.properties(**{
          '$build/test_utils': {
              'should_exonerate_flaky_failures': True,
          },
      }),
      api.override_step_data(
          'query LUCI Analysis for failure rates.rpc call', retcode=1),
      api.post_process(post_process.MustRun,
                       'error querying LUCI Analysis for failure rates'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'immune to ill-formed response',
      api.chromium.generic_build(
          builder_group='fake-group',
          builder='fake-builder',
          experiments=['enable_weetbix_queries']),
      api.properties(**{
          '$build/test_utils': {
              'should_exonerate_flaky_failures': True,
          },
      }),
      api.step_data(
          'query LUCI Analysis for failure rates.rpc call',
          stdout=api.raw_io.output_text(api.json.dumps({'testVariants': []})),
      ),
      api.post_process(post_process.MustRun,
                       'error querying LUCI Analysis for failure rates'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'immune to another ill-formed response',
      api.chromium.generic_build(
          builder_group='fake-group',
          builder='fake-builder',
      ),
      api.properties(**{
          '$build/test_utils': {
              'should_exonerate_flaky_failures': True,
          },
      }),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'empty response',
      api.chromium.generic_build(
          builder_group='fake-group',
          builder='fake-builder',
          experiments=['enable_weetbix_queries']),
      api.properties(**{
          '$build/test_utils': {
              'should_exonerate_flaky_failures': True,
          },
      }),
      api.step_data(
          'query LUCI Analysis for failure rates.rpc call',
          stdout=api.raw_io.output_text(api.json.dumps({})),
      ),
      api.post_process(post_process.MustRun,
                       'error querying LUCI Analysis for failure rates'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no failed tests',
      api.chromium.generic_build(
          builder_group='fake-group',
          builder='fake-builder',
          experiments=['enable_weetbix_queries']),
      api.properties(
          exclude_failed_test=True,
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.post_process(post_process.DoesNotRun,
                       'query LUCI Analysis for failure rates'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no tests are marked as known flaky or recently failing',
      api.chromium.generic_build(
          builder_group='fake-group',
          builder='fake-builder',
      ),
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
      api.luci_analysis.query_failure_rate_results([
          api.luci_analysis.generate_analysis(
              test_id='ninja://failed_test/testA',
              expected_count=10,
              unexpected_count=0),
          api.luci_analysis.generate_analysis(
              test_id='ninja://failed_test/testB',
              expected_count=10,
              unexpected_count=0),
      ]),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  def CheckStepInput(check,
                     step_odict,
                     step_name,
                     test_name,
                     should_contain=True):
    step = step_odict[step_name]
    if should_contain:
      check(test_name in step.stdin)
    else:
      check(test_name not in step.stdin)

  yield api.test(
      'part of the tests are marked as known flaky',
      api.chromium.generic_build(
          builder_group='fake-group',
          builder='fake-builder',
      ),
      api.properties(
          known_luci_analysis_flakes_expectations={
              'failed_test': ['testA'],
          },
          weak_flaky_failures={
              'failed_test': ['testA'],
          },
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.override_step_data(
          'failed_test results',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  'failed_test', failing_tests=['testA', 'testB']))),
      api.luci_analysis.query_failure_rate_results([
          api.luci_analysis.generate_analysis(
              test_id='ninja://failed_test/testA',
              flaky_verdict_counts=[10],
              examples_times=[60 * 60 * 12],
          ),
          api.luci_analysis.generate_analysis(
              test_id='ninja://failed_test/testB'),
      ]),
      api.post_process(CheckStepInput, 'exonerate unrelated test failures',
                       'testA'),
      api.post_process(
          CheckStepInput,
          'exonerate unrelated test failures',
          'testB',
          should_contain=False),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'all tests were skipped',
      api.chromium.generic_build(
          builder_group='fake-group',
          builder='fake-builder',
      ),
      api.properties(
          known_luci_analysis_flakes_expectations={},
          weak_flaky_failures={},
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.override_step_data(
          'failed_test results',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  'failed_test', skipped_tests=['testA']))),
      api.luci_analysis.query_failure_rate_results([
          api.luci_analysis.generate_analysis(
              test_id='ninja://failed_test/testA', flaky_verdict_counts=[10]),
      ]),
      api.post_process(post_process.DoesNotRun,
                       'exonerate unrelated test failures'),
      api.post_process(post_process.MustRun,
                       'failed_test (retry shards with patch)'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'all of the tests are marked as known flaky',
      api.chromium.generic_build(
          builder_group='fake-group',
          builder='fake-builder',
      ),
      api.override_step_data(
          'failed_test results',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  'failed_test', failing_tests=['testA', 'testB']))),
      api.properties(
          known_luci_analysis_flakes_expectations={
              'failed_test': ['testA', 'testB'],
          },
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.time.seed(60 * 60 * 12),
      api.luci_analysis.query_failure_rate_results([
          api.luci_analysis.generate_analysis(
              test_id='ninja://failed_test/testA',
              flaky_verdict_counts=[10],
              examples_times=[60 * 60 * 12]),
          api.luci_analysis.generate_analysis(
              test_id='ninja://failed_test/testB',
              flaky_verdict_counts=[10],
              examples_times=[60 * 60 * 12]),
      ]),
      api.post_process(CheckStepInput, 'exonerate unrelated test failures',
                       'testA'),
      api.post_process(CheckStepInput, 'exonerate unrelated test failures',
                       'testB'),
      # Ensure LUCI Analysis is in the explaination
      api.post_process(CheckStepInput, 'exonerate unrelated test failures',
                       'LUCI Analysis'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'tests are deterministically failing',
      api.chromium.generic_build(
          builder_group='fake-group',
          builder='fake-builder',
          experiments=['enable_weetbix_queries'],
      ),
      api.override_step_data(
          'failed_test results',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  'failed_test', failing_tests=['testA']))),
      api.properties(
          known_luci_analysis_flakes_expectations={
              'failed_test': ['testA'],
          },
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.luci_analysis.query_failure_rate_results([
          api.luci_analysis.generate_analysis(
              test_id='ninja://failed_test/testA',
              expected_count=1,
              unexpected_count=9,
              examples_times=[60 * 60 * 12]),
      ]),
      api.post_process(post_process.PropertiesContain, 'luci_analysis_info'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'skip querying if there are too many failures',
      api.chromium.generic_build(
          builder_group='fake-group',
          builder='fake-builder',
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
                       'query LUCI Analysis for failure rates'),
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
          builder_group='fake-group',
          builder='fake-builder',
          experiments=['enable_weetbix_queries']),
      api.override_step_data(
          'failed_test results',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  'failed_test', failing_tests=['testA', 'testB']))),
      api.properties(
          has_too_many_failures=True,
          known_luci_analysis_flakes_expectations={
              'failed_test': ['testA', 'testB'],
          },
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.luci_analysis.query_failure_rate_results([
          api.luci_analysis.generate_analysis(
              test_id='ninja://failed_test/testA', unexpected_count=10),
          api.luci_analysis.generate_analysis(
              test_id='ninja://failed_test/testB', unexpected_count=10),
      ]),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_weak_weetbix_exonerations does not run strongly exonerated',
      api.chromium.generic_build(
          builder_group='fake-group', builder='fake-builder'),
      api.properties(
          known_luci_analysis_flakes_expectations={
              'failed_test': ['testA', 'testB'],
          },
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.time.seed(60 * 60 * 12),
      api.override_step_data(
          'failed_test results',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  'failed_test', failing_tests=['testA', 'testB']))),
      api.luci_analysis.query_failure_rate_results([
          api.luci_analysis.generate_analysis(
              test_id='ninja://failed_test/testA',
              flaky_verdict_counts=[10],
              examples_times=[60 * 60 * 12]),
          api.luci_analysis.generate_analysis(
              test_id='ninja://failed_test/testB',
              flaky_verdict_counts=[10],
              examples_times=[60 * 60 * 12]),
      ]),
      api.post_process(post_process.MustRun, 'failed_test (with patch)'),
      api.post_process(post_process.DoesNotRun,
                       'failed_test (retry shards with patch)'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_weak_weetbix_exonerations does run weakly exonerated',
      api.chromium.generic_build(
          builder_group='fake-group', builder='fake-builder'),
      api.properties(
          known_luci_analysis_flakes_expectations={
              'failed_test': ['testA', 'testB'],
          },
          weak_flaky_failures={
              'failed_test': ['testA', 'testB'],
          },
          # Need to make sure the retry step isn't because of an invalid test
          all_valid=True,
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.override_step_data(
          'failed_test results',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  'failed_test', failing_tests=['testA', 'testB']))),
      api.luci_analysis.query_failure_rate_results([
          api.luci_analysis.generate_analysis(
              test_id='ninja://failed_test/testA', flaky_verdict_counts=[10]),
          api.luci_analysis.generate_analysis(
              test_id='ninja://failed_test/testB', flaky_verdict_counts=[10]),
      ]),
      api.post_process(post_process.MustRun, 'failed_test (with patch)'),
      api.post_process(post_process.MustRun,
                       'failed_test (retry shards with patch)'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'does not exonerate over 100',
      api.chromium.generic_build(
          builder_group='fake-group', builder='fake-builder'),
      api.properties(
          known_luci_analysis_flakes_expectations={
              'failed_test': [],
          },
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.override_step_data(
          'failed_test results',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  'failed_test',
                  failing_tests=['test%d' % t for t in range(101)]))),
      api.post_process(post_process.DoesNotRun,
                       'query LUCI Analysis for failure rates.rpc call'),
      api.post_process(post_process.StepTextContains,
                       'Skipping querying LUCI Analysis for failure rates',
                       ['101']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
