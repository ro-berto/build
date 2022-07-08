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
    'expected_flaky_test_ids': Property(kind=Dict()),
    'num_intervals': Property(kind=int),
    'min_flake_count': Property(kind=int),
    'empty_response': Property(kind=bool, default=False),
}


def RunSteps(
    api,
    test_suite_to_results,
    expected_flaky_test_ids,
    num_intervals,
    min_flake_count,
    empty_response,
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

  if expected_flaky_test_ids == {}:
    for suite_name, failure_rate_per_suite in (
        suite_to_failure_rate_per_suite.items()):
      api.assertions.assertEqual(
          len(
              failure_rate_per_suite.get_flaky_tests(num_intervals,
                                                     min_flake_count)), 0)
  for suite_name, expected_flaky_test_ids in expected_flaky_test_ids.items():
    api.assertions.assertIn(suite_name, suite_to_failure_rate_per_suite)
    flaky_tests = suite_to_failure_rate_per_suite[suite_name].get_flaky_tests(
        num_intervals, min_flake_count)
    api.assertions.assertEqual(flaky_tests, expected_flaky_test_ids)


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
                  'totalRunUnexpectedVerdicts': 1,
                  'totalRunFlakyVerdicts': 3,
              },
              {
                  'intervalAge': 2,
                  'totalRunExpectedVerdicts': 300,
                  'totalRunFlakyVerdicts': 10,
              },
          ],
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
                  'totalRunUnexpectedVerdicts': 1,
              },
              {
                  'intervalAge': 2,
                  'totalRunExpectedVerdicts': 300,
                  'totalRunUnexpectedVerdicts': 3,
              },
          ],
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
      },
  ]
  yield api.test(
      'basic',
      api.properties(
          test_suite_to_results=test_suite_to_results,
          expected_flaky_test_ids={
              'suite_1': ['ninja://gpu:suite_1/test_one',],
          },
          num_intervals=2,
          min_flake_count=11,
      ),
      api.step_data(
          'query weetbix for failure rates.rpc call',
          stdout=api.raw_io.output_text(
              api.json.dumps({
                  'test_variants': test_variants_response,
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
      'small_num_interval',
      api.properties(
          test_suite_to_results=test_suite_to_results,
          expected_flaky_test_ids={
              'suite_1': ['ninja://gpu:suite_1/test_one',],
          },
          num_intervals=1,
          min_flake_count=3,
      ),
      api.step_data(
          'query weetbix for failure rates.rpc call',
          stdout=api.raw_io.output_text(
              api.json.dumps({
                  'test_variants': test_variants_response,
              }),),
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'small_num_interval_no_flakes',
      api.properties(
          test_suite_to_results=test_suite_to_results,
          expected_flaky_test_ids={},
          num_intervals=1,
          min_flake_count=10,
      ),
      api.step_data(
          'query weetbix for failure rates.rpc call',
          stdout=api.raw_io.output_text(
              api.json.dumps({
                  'test_variants': test_variants_response,
              }),),
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'empty_response',
      api.properties(
          test_suite_to_results=test_suite_to_results,
          empty_response=True,
          expected_flaky_test_ids={},
          num_intervals=None,
          min_flake_count=None,
      ),
      api.step_data(
          'query weetbix for failure rates.rpc call',
          stdout=api.raw_io.output_text(api.json.dumps({})),
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
