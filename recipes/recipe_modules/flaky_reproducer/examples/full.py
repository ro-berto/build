# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.recipe_api import Property

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'flaky_reproducer',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/resultdb',
    'recipe_engine/swarming',
]

PROPERTIES = {
    'task_id':
        Property(default=None, kind=str),
    'test_name':
        Property(default=None, kind=str),
    'trigger':
        Property(
            default='auto',
            help="The task is (manual|auto)-ly triggerd.",
            kind=str),
}


def RunSteps(api, trigger, task_id, test_name):
  api.flaky_reproducer.set_config(trigger)
  return api.flaky_reproducer.run(task_id, test_name)


from google.protobuf import timestamp_pb2

from recipe_engine.post_process import (DropExpectation, StatusFailure,
                                        ResultReason)
from PB.go.chromium.org.luci.resultdb.proto.v1 import (
    common as common_pb2,  # go/pyformat-break
    invocation as invocation_pb2,  #
    resultdb as resultdb_pb2,  #
    test_result as test_result_pb2,  #
)


def GenTests(api):
  success_swarming_results = [
      api.swarming.task_result(
          id='0',
          name='flaky reproducer strategy repeat for MockUnitTests.FailTest',
          state=api.swarming.TaskState.COMPLETED,
          output='some-output',
          outputs=('reproducing_step.json',)),
      api.swarming.task_result(
          id='1',
          name='flaky reproducer strategy batch for MockUnitTests.FailTest',
          state=api.swarming.TaskState.COMPLETED,
          output='some-output',
          outputs=()),
  ]
  resultdb_invocation = api.resultdb.Invocation(
      proto=invocation_pb2.Invocation(
          state=invocation_pb2.Invocation.FINALIZED,
          realm='chromium:ci',
      ),
      test_results=[
          test_result_pb2.TestResult(
              test_id='ninja://base:base_unittests/MockUnitTests.FailTest',
              name='test_name_1',
              expected=False,
              status=test_result_pb2.FAIL,
              start_time=timestamp_pb2.Timestamp(seconds=1658269605),
              variant=common_pb2.Variant(
                  **{
                      'def': {
                          'builder': 'Linux Tests',
                          'test_suite': 'base_unittests',
                      }
                  }),
              tags=[
                  common_pb2.StringPair(
                      key="test_name", value="MockUnitTests.FailTest"),
              ],
          ),
      ],
  )
  test_running_history = resultdb_pb2.GetTestResultHistoryResponse(entries=[
      resultdb_pb2.GetTestResultHistoryResponse.Entry(
          result=test_result_pb2.TestResult(
              test_id='ninja://base:base_unittests/MockUnitTests.FailTest',
              name=('invocations/task-example.swarmingserver.appspot.com'
                    '-54321fffffabc001/result-1'),
              variant=common_pb2.Variant(
                  **{'def': {
                      'builder': 'Win10 Tests x64',
                  }}),
          )),
      resultdb_pb2.GetTestResultHistoryResponse.Entry(
          result=test_result_pb2.TestResult(
              test_id='ninja://base:base_unittests/MockUnitTests.FailTest',
              name='unknown-name-format',
              variant=common_pb2.Variant(**{'def': {
                  'builder': 'Mac11 Tests',
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
  verify_swarming_result = lambda id: api.swarming.task_result(
      id=id,
      name='flaky reproducer verify on Linux Tests for MockUnitTests.FailTest',
      state=api.swarming.TaskState.COMPLETED,
      output='some-output',
      outputs=('result_summary_0.json', 'result_summary_1.json'))
  yield api.test(
      'happy_path',
      api.properties(
          task_id='54321fffffabc123',
          test_name='MockUnitTests.FailTest',
          trigger='manual'),
      api.step_data(
          'get_test_result_summary.download swarming outputs',
          api.raw_io.output_dir({
              'output.json':
                  api.flaky_reproducer.get_test_data('gtest_good_output.json'),
          })),
      api.step_data(
          'get_test_binary from 54321fffffabc123',
          api.json.output_stream(
              api.json.loads(
                  api.flaky_reproducer.get_test_data(
                      'gtest_task_request.json')))),
      api.step_data('collect strategy results',
                    api.swarming.collect(success_swarming_results)),
      api.step_data(
          'collect_strategy_results.load ReproducingStep',
          api.file.read_json(
              api.json.loads(
                  api.flaky_reproducer.get_test_data(
                      'reproducing_step.json')))),
      api.resultdb.query(
          {
              'task-example.swarmingserver.appspot.com-54321fffffabc123':
                  resultdb_invocation,
          },
          step_name='verify_reproducing_step.rdb query'),
      api.resultdb.get_test_result_history(
          test_running_history,
          step_name='verify_reproducing_step.get_test_result_history'),
      api.step_data(
          'verify_reproducing_step.get_test_binary from 54321fffffabc001',
          api.json.output_stream(
              api.json.loads(
                  api.flaky_reproducer.get_test_data(
                      'gtest_task_request.json')))),
      api.step_data(
          'verify_reproducing_step.collect verify results',
          api.swarming.collect(
              [verify_swarming_result('2'),
               verify_swarming_result('3')])),
      api.step_data(
          'verify_reproducing_step.load verify result',
          api.file.read_json(
              api.json.loads(
                  api.flaky_reproducer.get_test_data(
                      'gtest_good_output.json')))),
      api.step_data(
          'verify_reproducing_step.load verify result (2)',
          api.file.read_json(
              api.json.loads(
                  api.flaky_reproducer.get_test_data(
                      'gtest_good_output.json')))),
  )

  yield api.test(
      'no_exists_task_result',
      api.properties(
          task_id='54321fffffabc123', test_name='MockUnitTests.FailTest'),
      api.step_data('get_test_result_summary.swarming collect',
                    api.swarming.collect([])),
      api.post_process(StatusFailure),
      api.post_process(ResultReason,
                       'Cannot find TaskResult for task 54321fffffabc123.'),
      api.post_process(DropExpectation),
  )

  yield api.test(
      'not_supported_task_result',
      api.properties(
          task_id='54321fffffabc123', test_name='MockUnitTests.FailTest'),
      api.step_data('get_test_result_summary.download swarming outputs',
                    api.raw_io.output_dir({})),
      api.post_process(StatusFailure),
      api.post_process(ResultReason, 'Not supported task result.'),
      api.post_process(DropExpectation),
  )

  success_swarming_result_without_reproducing_step = api.swarming.task_result(
      id='0',
      name='flaky reproducer strategy batch for MockUnitTests.FailTest',
      state=api.swarming.TaskState.COMPLETED,
      output='some-output',
  )
  yield api.test(
      'strategy_without_result',
      api.properties(
          task_id='54321fffffabc123',
          test_name='MockUnitTests.FailTest',
          trigger='manual'),
      api.step_data(
          'get_test_result_summary.download swarming outputs',
          api.raw_io.output_dir({
              'output.json':
                  api.flaky_reproducer.get_test_data('gtest_good_output.json'),
          })),
      api.step_data(
          'get_test_binary from 54321fffffabc123',
          api.json.output_stream(
              api.json.loads(
                  api.flaky_reproducer.get_test_data(
                      'gtest_task_request.json')))),
      api.step_data(
          'collect strategy results',
          api.swarming.collect(
              [success_swarming_result_without_reproducing_step])),
  )

  yield api.test(
      'test_name_not_in_test_result',
      api.properties(task_id='54321fffffabc123', test_name='NotExists.Test'),
      api.step_data(
          'get_test_result_summary.download swarming outputs',
          api.raw_io.output_dir({
              'output.json':
                  api.flaky_reproducer.get_test_data('gtest_good_output.json'),
          })),
  )

  yield api.test(
      'unknown_result_summary',
      api.properties(task_id='54321fffffabc123', test_name='NotExists.Test'),
      api.step_data('get_test_result_summary.download swarming outputs',
                    api.raw_io.output_dir({'output.json': b'{}'})),
  )
