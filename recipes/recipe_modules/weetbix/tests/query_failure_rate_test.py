# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Tests for query_failure_rate."""
from recipe_engine import post_process
from recipe_engine.config import Dict
from recipe_engine.config import List
from recipe_engine.recipe_api import Property
from RECIPE_MODULES.build.test_utils.util import RDBPerIndividualTestResults
from RECIPE_MODULES.build.chromium_tests import steps
from RECIPE_MODULES.build.test_utils.util import RDBPerSuiteResults

from PB.go.chromium.org.luci.resultdb.proto.v1 import (test_result as
                                                       test_result_pb2)

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'chromium_tests',
    'weetbix',
    'recipe_engine/assertions',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
]

PROPERTIES = {
    'test_suite_to_results': Property(kind=list),
    'num_intervals_list': Property(kind=list),
    'empty_response': Property(kind=bool, default=False),
    'expected_flake_and_unexpected_dict': Property(kind=Dict(), default=None),
}


def RunSteps(
    api,
    test_suite_to_results,
    num_intervals_list,
    empty_response,
    expected_flake_and_unexpected_dict,
):
  tests = []
  for suite_to_results in test_suite_to_results:
    for suite, results in suite_to_results.items():
      test_spec = steps.SwarmingIsolatedScriptTestSpec.create(suite)
      test = test_spec.get_test(api.chromium_tests)

      test.update_rdb_results(
          'with patch',
          RDBPerSuiteResults(
              suite_name=suite,
              variant_hash='8897b2a859b391d5',
              total_tests_ran=len(results['passing']) + len(results['failing']),
              unexpected_passing_tests=results['passing'],
              unexpected_failing_tests=results['failing'],
              unexpected_skipped_tests=set(),
              all_tests=results['passing'].union(results['failing']),
              individual_unexpected_test_by_test_name={
                  result.test_name: result for result in results['failing']
              },
              invalid=False,
              test_id_prefix=''))
    tests.append(test)

  suite_to_failure_rate_per_suite = api.weetbix.query_failure_rate(tests)

  if empty_response:
    api.assertions.assertEqual(suite_to_failure_rate_per_suite, {})
    return

  for suite_name, expected_dict in expected_flake_and_unexpected_dict.items():
    api.assertions.assertIn(suite_name, suite_to_failure_rate_per_suite)
    suite_analysis = suite_to_failure_rate_per_suite[suite_name]
    for individual_analysis in suite_analysis.failure_analysis_list:
      flaky_and_unexpected_counts = {
          'total_flaky':
              individual_analysis.get_flaky_verdict_counts(num_intervals_list),
          'total_recent_unexpected':
              (individual_analysis.get_unexpected_recent_verdict_count()),
      }
      api.assertions.assertDictEqual(
          flaky_and_unexpected_counts,
          expected_dict[individual_analysis.test_id],
      )


def GenTests(api):
  test_suite_to_results = [
      {
          'suite_1': {
              'failing':
                  set([
                      RDBPerIndividualTestResults(
                          test_name='test_one',
                          test_id='ninja://gpu:suite_1/test_one',
                          statuses=[test_result_pb2.FAIL, test_result_pb2.FAIL],
                          expectednesses=[False, False],
                          failure_reasons=['failure reason', ''],
                      ),
                  ]),
              'passing':
                  set()
          }
      },
      {
          'suite_2': {
              'failing':
                  set([
                      RDBPerIndividualTestResults(
                          test_name='test_one',
                          test_id='ninja://gpu:suite_2/test_one',
                          statuses=[test_result_pb2.FAIL, test_result_pb2.FAIL],
                          expectednesses=[False, False],
                          failure_reasons=['failure reason', ''],
                      ),
                  ]),
              'passing':
                  set()
          }
      },
      {
          'suite_3': {
              'failing':
                  set([
                      RDBPerIndividualTestResults(
                          test_name='test_two',
                          test_id='ninja://gpu:suite_3/test_two',
                          statuses=[test_result_pb2.FAIL, test_result_pb2.FAIL],
                          expectednesses=[False, False],
                          failure_reasons=['failure reason', ''],
                      ),
                      RDBPerIndividualTestResults(
                          test_name='test_three',
                          test_id='ninja://gpu:suite_3/test_three',
                          statuses=[test_result_pb2.FAIL, test_result_pb2.FAIL],
                          expectednesses=[False, False],
                          failure_reasons=['failure reason', ''],
                      ),
                  ]),
              'passing':
                  set([
                      RDBPerIndividualTestResults(
                          test_name='test_one',
                          test_id='ninja://gpu:suite_3/test_one',
                          statuses=[test_result_pb2.PASS],
                          expectednesses=[True],
                          failure_reasons=[],
                      ),
                  ]),
          }
      },
  ]

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

  test_variants_response = [
      {
          'testId':
              'ninja://gpu:suite_1/test_one',
          'variantHash':
              '8897b2a859b391d5',
          'intervalStats': [
              {
                  'intervalAge': 1,
                  'totalRunExpectedVerdicts': 300,
                  'totalRunUnexpectedVerdicts': 2,
                  'totalRunFlakyVerdicts': 3,
              },
              {
                  'intervalAge': 2,
                  'totalRunExpectedVerdicts': 300,
                  'totalRunFlakyVerdicts': 10,
              },
              {
                  'intervalAge': 3,
                  'totalRunExpectedVerdicts': 300,
                  'totalRunFlakyVerdicts': 10,
              },
          ],
          'recentVerdicts':
              construct_recent_verdicts(
                  expected_count=8,
                  unexpected_count=2,
              )
      },
      {
          'testId':
              'ninja://gpu:suite_2/test_one',
          'variantHash':
              '8897b2a859b39abc',
          'intervalStats': [
              {
                  'intervalAge': 1,
                  'totalRunExpectedVerdicts': 300,
                  'totalRunUnexpectedVerdicts': 9,
              },
              {
                  'intervalAge': 2,
                  'totalRunExpectedVerdicts': 300,
                  'totalRunUnexpectedVerdicts': 0,
              },
          ],
          'recentVerdicts':
              construct_recent_verdicts(
                  expected_count=1,
                  unexpected_count=9,
              )
      },
      {
          'testId':
              'ninja://gpu:suite_3/test_one',
          'variantHash':
              '8897b2a859b39abc',
          'intervalStats': [
              {
                  'intervalAge': 1,
                  'totalRunExpectedVerdicts': 300,
                  'totalRunUnexpectedVerdicts': 1,
              },
              {
                  'intervalAge': 2,
                  'totalRunExpectedVerdicts': 300,
                  'totalRunUnexpectedVerdicts': 3,
              },
          ],
          'recentVerdicts':
              construct_recent_verdicts(
                  expected_count=9,
                  unexpected_count=1,
              )
      },
      {
          'testId':
              'ninja://gpu:suite_3/test_two',
          'variantHash':
              '8897b2a859b39abc',
          'intervalStats': [
              {
                  'intervalAge': 1,
                  'totalRunExpectedVerdicts': 300,
                  'totalRunUnexpectedVerdicts': 1,
              },
              {
                  'intervalAge': 2,
                  'totalRunExpectedVerdicts': 300,
                  'totalRunUnexpectedVerdicts': 3,
              },
          ],
          'recentVerdicts':
              construct_recent_verdicts(
                  expected_count=10,
                  unexpected_count=0,
              )
      },
  ]
  yield api.test(
      'basic',
      api.properties(
          test_suite_to_results=test_suite_to_results,
          num_intervals_list=[1, 5],
          expected_flake_and_unexpected_dict={
              'suite_1': {
                  'ninja://gpu:suite_1/test_one': {
                      'total_flaky': {
                          1: 3,
                          5: 23
                      },
                      'total_recent_unexpected': 2,
                  }
              },
              'suite_2': {
                  'ninja://gpu:suite_2/test_one': {
                      'total_flaky': {
                          1: 0,
                          5: 0
                      },
                      'total_recent_unexpected': 9,
                  }
              },
          },
      ),
      api.step_data(
          'query weetbix for failure rates.rpc call',
          stdout=api.raw_io.output_text(
              api.json.dumps({
                  'testVariants': test_variants_response,
              }),),
      ),
      api.post_process(
          post_process.LogContains,
          'query weetbix for failure rates.rpc call',
          'input',
          [
              'ninja://gpu:suite_1/test_one',
              'ninja://gpu:suite_2/test_one',
          ],
      ),
      api.post_process(
          post_process.LogDoesNotContain,
          'query weetbix for failure rates.rpc call',
          'input',
          [
              'ninja://gpu:suite_3/test_one',
          ],
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'empty_response',
      api.properties(
          test_suite_to_results=test_suite_to_results,
          empty_response=True,
          num_intervals_list=None,
      ),
      api.step_data(
          'query weetbix for failure rates.rpc call',
          stdout=api.raw_io.output_text(api.json.dumps({})),
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
