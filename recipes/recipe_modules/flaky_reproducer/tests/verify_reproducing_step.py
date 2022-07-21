# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.recipe_api import Property
from RECIPE_MODULES.build.flaky_reproducer.libs import (ReproducingStep,
                                                        UnexpectedTestResult)

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'flaky_reproducer',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/resultdb',
    'recipe_engine/step',
    'recipe_engine/swarming',
]

PROPERTIES = {
    'task_id': Property(default=None, kind=str),
    'failing_sample': Property(default=None),
    'reproducing_step_data': Property(default=None),
}


def RunSteps(api, task_id, failing_sample, reproducing_step_data):
  api.flaky_reproducer.set_config('auto')
  if reproducing_step_data:
    reproducing_step = ReproducingStep.from_jsonish(reproducing_step_data)
  else:
    reproducing_step = None
  builder_results = api.flaky_reproducer.verify_reproducing_step(
      task_id, failing_sample, reproducing_step)
  api.flaky_reproducer.summarize_results(reproducing_step, builder_results)


import re
from google.protobuf import timestamp_pb2

from recipe_engine import post_process
from PB.go.chromium.org.luci.resultdb.proto.v1 import (
    common as common_pb2,  # go/pyformat-break
    invocation as invocation_pb2,  #
    resultdb as resultdb_pb2,  #
    test_result as test_result_pb2,  #
)


def GenTests(api):
  resultdb_invocation = api.resultdb.Invocation(
      proto=invocation_pb2.Invocation(
          state=invocation_pb2.Invocation.FINALIZED,
          realm='chromium:ci',
          create_time=timestamp_pb2.Timestamp(seconds=1658269605),
          finalize_time=timestamp_pb2.Timestamp(seconds=1658269605),
      ),
      test_results=[
          test_result_pb2.TestResult(
              test_id='ninja://base:base_unittests/MockUnitTests.FailTest',
              name='test_name_1',
              expected=False,
              status=test_result_pb2.FAIL,
              tags=[
                  common_pb2.StringPair(
                      key="test_name", value="MockUnitTests.FailTest"),
              ],
          ),
      ],
  )
  empty_running_history = resultdb_pb2.GetTestResultHistoryResponse()
  test_running_history = resultdb_pb2.GetTestResultHistoryResponse(entries=[
      resultdb_pb2.GetTestResultHistoryResponse.Entry(
          result=test_result_pb2.TestResult(
              test_id='ninja://base:base_unittests/MockUnitTests.FailTest',
              name=('invocations/task-example.swarmingserver.appspot.com'
                    '-54321fffffabc001/result-1'),
              variant=common_pb2.Variant(**{'def': {
                  'builder': 'Linux Tests',
              }}),
          )),
      resultdb_pb2.GetTestResultHistoryResponse.Entry(
          result=test_result_pb2.TestResult(
              test_id='ninja://base:base_unittests/MockUnitTests.FailTest',
              name='unknown-name-format',
              variant=common_pb2.Variant(**{'def': {
                  'builder': 'Linux Tests',
              }}),
          )),
      resultdb_pb2.GetTestResultHistoryResponse.Entry(
          result=test_result_pb2.TestResult(
              test_id='ninja://base:base_unittests/MockUnitTests.FailTest',
              name=('invocations/task-example.swarmingserver.appspot.com'
                    '-54321fffffabc001/result-1'),
              variant=common_pb2.Variant(
                  **{'def': {
                      'builder': 'Not Supported Builder',
                  }}),
          )),
  ])

  yield api.test(
      'cannot_retrieve_invocation',
      api.properties(
          task_id='some-task-id',
          failing_sample=UnexpectedTestResult('some-test')),
      api.post_check(post_process.StatusFailure),
      api.post_check(post_process.ResultReason,
                     'Cannot retrieve invocation for task some-task-id.'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'cannot_find_test_result_for_test',
      api.properties(
          task_id='some-task-id',
          failing_sample=UnexpectedTestResult('Not.Exists.Test')),
      api.resultdb.query(
          {
              'task-example.swarmingserver.appspot.com-some-task-id':
                  resultdb_invocation,
          },
          step_name='verify_reproducing_step.rdb query'),
      api.post_check(post_process.StatusFailure),
      api.post_check(post_process.ResultReason,
                     'Cannot find TestResult for test Not.Exists.Test.'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no_verify_builders_and_no_reproducing_step',
      api.properties(
          task_id='some-task-id',
          failing_sample=UnexpectedTestResult('MockUnitTests.FailTest')),
      api.resultdb.query(
          {
              'task-example.swarmingserver.appspot.com-some-task-id':
                  resultdb_invocation,
          },
          step_name='verify_reproducing_step.rdb query'),
      api.resultdb.get_test_result_history(
          empty_running_history,
          step_name='verify_reproducing_step.get_test_result_history'),
      api.post_check(post_process.StepTextEquals, 'summarize_results',
                     'Not reproducible.'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'verify_builder_failed',
      api.properties(
          task_id='some-task-id',
          failing_sample=UnexpectedTestResult('MockUnitTests.FailTest'),
          reproducing_step_data=api.json.loads(
              api.flaky_reproducer.get_test_data('reproducing_step.json')),
      ),
      api.resultdb.query(
          {
              'task-example.swarmingserver.appspot.com-some-task-id':
                  resultdb_invocation,
          },
          step_name='verify_reproducing_step.rdb query'),
      api.resultdb.get_test_result_history(
          test_running_history,
          step_name='verify_reproducing_step.get_test_result_history'),
      api.step_data(
          'verify_reproducing_step.get_test_binary.show request',
          api.json.output_stream(
              api.json.loads(
                  api.flaky_reproducer.get_test_data(
                      'gtest_task_request.json')))),
      api.step_data(
          'verify_reproducing_step.collect verify results',
          api.swarming.collect([
              api.swarming.task_result(
                  '0', 'name', failure=True, output='failed-output'),
          ])),
      api.post_check(lambda check, steps: check(
          steps['summarize_results'].step_summary_text,
          re.search(r"Linux Tests failed:", steps['summarize_results'].
                    step_summary_text))),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  verify_swarming_result = api.swarming.task_result(
      id='0',
      name='flaky reproducer verify on Linux Tests for MockUnitTests.FailTest',
      state=api.swarming.TaskState.COMPLETED,
      output='some-output',
      outputs=('result_summary_0.json',))
  gtest_empty_result = api.json.loads(
      api.flaky_reproducer.get_test_data('gtest_good_output.json'))
  gtest_empty_result['per_iteration_data'] = []
  yield api.test(
      'verify_not_reproducible',
      api.properties(
          task_id='some-task-id',
          failing_sample=UnexpectedTestResult('MockUnitTests.FailTest'),
          reproducing_step_data=api.json.loads(
              api.flaky_reproducer.get_test_data('reproducing_step.json')),
      ),
      api.resultdb.query(
          {
              'task-example.swarmingserver.appspot.com-some-task-id':
                  resultdb_invocation,
          },
          step_name='verify_reproducing_step.rdb query'),
      api.resultdb.get_test_result_history(
          test_running_history,
          step_name='verify_reproducing_step.get_test_result_history'),
      api.step_data(
          'verify_reproducing_step.get_test_binary.show request',
          api.json.output_stream(
              api.json.loads(
                  api.flaky_reproducer.get_test_data(
                      'gtest_task_request.json')))),
      api.step_data('verify_reproducing_step.collect verify results',
                    api.swarming.collect([verify_swarming_result])),
      api.step_data('verify_reproducing_step.load verify result',
                    api.file.read_json(gtest_empty_result)),
      api.post_check(lambda check, steps: check(
          steps['summarize_results'].step_summary_text,
          re.search(r"not reproduced", steps['summarize_results'].
                    step_summary_text))),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  bad_task_request = api.json.loads(
      api.flaky_reproducer.get_test_data('gtest_task_request.json'))
  bad_task_request['task_slices'][0]['properties']['command'] = [
      'unknown', 'wrapper'
  ]
  yield api.test(
      'unknown_test_binary_wrapper',
      api.properties(
          task_id='some-task-id',
          failing_sample=UnexpectedTestResult('MockUnitTests.FailTest'),
          reproducing_step_data=api.json.loads(
              api.flaky_reproducer.get_test_data('reproducing_step.json')),
      ),
      api.resultdb.query(
          {
              'task-example.swarmingserver.appspot.com-some-task-id':
                  resultdb_invocation,
          },
          step_name='verify_reproducing_step.rdb query'),
      api.resultdb.get_test_result_history(
          test_running_history,
          step_name='verify_reproducing_step.get_test_result_history'),
      api.step_data('verify_reproducing_step.get_test_binary.show request',
                    api.json.output_stream(bad_task_request)),
      api.post_check(lambda check, steps: check(
          steps['summarize_results'].step_summary_text,
          re.search(
              r"Command line contains unknown wrapper: "
              r"\['unknown', 'wrapper'\]", steps['summarize_results'].
              step_summary_text))),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
