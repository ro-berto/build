# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Tests for cluster."""
from recipe_engine import recipe_test_api
from recipe_engine import post_process
from recipe_engine.config import Dict
from recipe_engine.config import List
from recipe_engine.recipe_api import Property
from RECIPE_MODULES.build.chromium_tests import steps
from RECIPE_MODULES.build.weetbix.api import CLUSTER_STEP_NAME
from RECIPE_MODULES.build.test_utils.util import RDBPerSuiteResults
from RECIPE_MODULES.build.test_utils.util import RDBPerIndividualTestResults

from PB.go.chromium.org.luci.resultdb.proto.v1 import (test_result as
                                                       test_result_pb2)

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'chromium_tests',
    'weetbix',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
]

PROPERTIES = {
    'test_suite_to_results': Property(kind=Dict()),
}


def RunSteps(api, test_suite_to_results):
  tests = []
  for suite, results in test_suite_to_results.items():
    test_spec = steps.SwarmingIsolatedScriptTestSpec.create(suite)
    test = test_spec.get_test(api.chromium_tests)

    test.update_rdb_results(
        'with patch',
        RDBPerSuiteResults(
            suite_name=suite,
            variant_hash='',
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
  api.weetbix.get_clusters_for_failing_test_results(tests)


def GenTests(api):
  yield api.test(
      'basic',
      api.properties(
          test_suite_to_results={
              'suite_1': {
                  'failing':
                      set([
                          RDBPerIndividualTestResults(
                              test_name='test_one',
                              test_id='ninja://gpu:suite_1/test_one',
                              statuses=[
                                  test_result_pb2.FAIL, test_result_pb2.FAIL
                              ],
                              expectednesses=[False, False],
                              failure_reasons=['failure reason', ''],
                          ),
                          RDBPerIndividualTestResults(
                              test_name='test_two',
                              test_id='ninja://gpu:suite_1/test_two',
                              statuses=[
                                  test_result_pb2.FAIL, test_result_pb2.FAIL
                              ],
                              expectednesses=[False, False],
                              failure_reasons=[
                                  'failure reason', 'different failure reason'
                              ],
                          ),
                      ]),
                  'passing':
                      set()
              },
              'suite_2': {
                  'failing':
                      set([
                          RDBPerIndividualTestResults(
                              test_name='test_one',
                              test_id='ninja://gpu:suite_2/test_one',
                              statuses=[
                                  test_result_pb2.FAIL, test_result_pb2.FAIL
                              ],
                              expectednesses=[False, False],
                              failure_reasons=[
                                  'failure reason', 'different failure reason'
                              ],
                          ),
                          RDBPerIndividualTestResults(
                              test_name='test_two',
                              test_id='ninja://gpu:suite_2/test_two',
                              statuses=[
                                  test_result_pb2.FAIL, test_result_pb2.FAIL
                              ],
                              expectednesses=[False, False],
                              failure_reasons=[
                                  'failure reason', 'different failure reason'
                              ],
                          ),
                      ]),
                  'passing':
                      set()
              }
          }),
      api.step_data(
          CLUSTER_STEP_NAME,
          stdout=api.raw_io.output_text(
              api.json.dumps({
                  'clusteredTestResults': [
                      {
                          'requestTag':
                              'ninja://gpu:suite_1_test_one_reason_0',
                          'clusters': [{
                              'clusterId': {
                                  'algorithm': 'rules',
                                  'id': 'fa4a547e837c48d87ea1f9dfb3d44173',
                                  'bug': {
                                      'system':
                                          'monorail',
                                      'id':
                                          '12345',
                                      'link_text':
                                          'crbug.com/12345',
                                      'url': (
                                          'bugs.chromium.org/p/chromium/issues/'
                                          'detail?id=12345'),
                                  },
                              }
                          }],
                      },
                      {
                          'requestTag':
                              'ninja://gpu:suite_1_test_two_reason_0',
                          'clusters': [{
                              'clusterId': {
                                  'algorithm': 'rules',
                                  'id': 'fa4a547e837c48d87ea1f9dfb3d44173',
                                  'bug': {
                                      'system':
                                          'monorail',
                                      'id':
                                          '12345',
                                      'link_text':
                                          'crbug.com/12345',
                                      'url': (
                                          'bugs.chromium.org/p/chromium/issues/'
                                          'detail?id=12345'),
                                  },
                              }
                          }],
                      },
                      {
                          'requestTag':
                              'ninja://gpu:suite_1_test_two_reason_1',
                          'clusters': [{
                              'clusterId': {
                                  'algorithm': 'rules',
                                  'id': 'fa4a547e837c48d87ea1f9dfb3d44173',
                                  'bug': {
                                      'system':
                                          'monorail',
                                      'id':
                                          '12345',
                                      'link_text':
                                          'crbug.com/12345',
                                      'url': (
                                          'bugs.chromium.org/p/chromium/issues/'
                                          'detail?id=12345'),
                                  },
                              }
                          }],
                      },
                      {
                          'requestTag':
                              'ninja://gpu:suite_2_test_one_reason_0',
                          'clusters': [{
                              'clusterId': {
                                  'algorithm': 'reason-v3',
                                  'id': 'fa4a547e837c48d87ea1f9dfb3d44173',
                              }
                          }],
                      },
                      {
                          'requestTag':
                              'ninja://gpu:suite_2_test_one_reason_1',
                          'clusters': [{
                              'clusterId': {
                                  'algorithm': 'reason-v3',
                                  'id': 'fa4a547e837c48d87ea1f9dfb3d44173',
                              }
                          }],
                      },
                      {
                          'requestTag':
                              'ninja://gpu:suite_2_test_two_reason_0',
                          'clusters': [{
                              'clusterId': {
                                  'algorithm': 'reason-v3',
                                  'id': 'fa4a547e837c48d87ea1f9dfb3d44173',
                              }
                          }],
                      },
                      {
                          'requestTag':
                              'ninja://gpu:suite_2_test_two_reason_1',
                          'clusters': [{
                              'clusterId': {
                                  'algorithm': 'reason-v3',
                                  'id': 'fa4a547e837c48d87ea1f9dfb3d44173',
                              }
                          }],
                      },
                  ]
              }))),
      api.post_process(
          post_process.LogContains,
          CLUSTER_STEP_NAME,
          'input',
          [
              '\"requestTag\": \"ninja://gpu:suite_1/test_one_reason_0\"',
              '\"requestTag\": \"ninja://gpu:suite_1/test_two_reason_0\"',
              '\"requestTag\": \"ninja://gpu:suite_1/test_two_reason_1\"',
              '\"requestTag\": \"ninja://gpu:suite_2/test_one_reason_0\"',
              '\"requestTag\": \"ninja://gpu:suite_2/test_one_reason_1\"',
          ],
      ),
      api.post_process(
          post_process.LogDoesNotContain,
          'cluster failing test results with weetbix',
          'input',
          [
              '\"requestTag\": \"ninja://gpu:suite_1/test_one_reason_1\"',
          ],
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'dont_cluster_for_passing_test',
      api.properties(
          test_suite_to_results={
              'suite_1': {
                  'failing':
                      set([
                          RDBPerIndividualTestResults(
                              test_name='failing_test',
                              test_id='ninja://gpu:suite_1/test_two',
                              statuses=[
                                  test_result_pb2.FAIL, test_result_pb2.FAIL
                              ],
                              expectednesses=[False, False],
                              failure_reasons=[
                                  'failure reason', 'different failure reason'
                              ],
                          ),
                      ]),
                  'passing':
                      set([
                          RDBPerIndividualTestResults(
                              test_name='passing_test',
                              test_id='ninja://gpu:suite_1/test_one',
                              statuses=[
                                  test_result_pb2.FAIL, test_result_pb2.PASS
                              ],
                              expectednesses=[False, True],
                              failure_reasons=['failure reason', ''],
                          )
                      ]),
              },
          }),
      api.step_data(
          CLUSTER_STEP_NAME,
          stdout=api.raw_io.output_text(
              api.json.dumps({
                  'clusteredTestResults': [{
                      'requestTag':
                          'ninja://gpu:suite_1_test_one_reason_0',
                      'clusters': [{
                          'clusterId': {
                              'algorithm': 'rules',
                              'id': 'fa4a547e837c48d87ea1f9dfb3d44173',
                              'bug': {
                                  'system':
                                      'monorail',
                                  'id':
                                      '12345',
                                  'link_text':
                                      'crbug.com/12345',
                                  'url': ('bugs.chromium.org/p/chromium/issues/'
                                          'detail?id=12345'),
                              },
                          }
                      }],
                  }]
              }),)),
      api.post_process(
          post_process.LogContains,
          CLUSTER_STEP_NAME,
          'input',
          [
              '\"requestTag\": \"ninja://gpu:suite_1/test_two_reason_0\"',
              '\"requestTag\": \"ninja://gpu:suite_1/test_two_reason_1\"',
          ],
      ),
      api.post_process(
          post_process.LogDoesNotContain,
          'cluster failing test results with weetbix',
          'input',
          ['ninja://gpu:suite_1/test_one'],
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no_failure_reasons',
      api.properties(
          test_suite_to_results={
              'suite_1': {
                  'failing':
                      set([
                          RDBPerIndividualTestResults(
                              test_name='passing_test',
                              test_id='ninja://gpu:suite_1/test_one',
                              statuses=[
                                  test_result_pb2.FAIL, test_result_pb2.FAIL
                              ],
                              expectednesses=[False, False],
                              failure_reasons=['', ''],
                          ),
                          RDBPerIndividualTestResults(
                              test_name='failing_test',
                              test_id='ninja://gpu:suite_1/test_two',
                              statuses=[
                                  test_result_pb2.FAIL, test_result_pb2.FAIL
                              ],
                              expectednesses=[False, False],
                              failure_reasons=['', ''],
                          ),
                      ]),
                  'passing':
                      set()
              }
          }),
      api.post_process(post_process.DoesNotRun, CLUSTER_STEP_NAME),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
