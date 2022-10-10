# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.recipe_api import Property

DEPS = [
    'flaky_reproducer',
    'recipe_engine/step',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/resultdb',
]

PROPERTIES = {
    'task_id': Property(default=None, kind=str),
    'build_id': Property(default=None, kind=str),
    'test_name': Property(default=None, kind=str),
    'test_id': Property(default=None, kind=str),
}


def RunSteps(api, task_id, build_id, test_name, test_id):
  ret = api.flaky_reproducer.query_resultdb_for_task_id_and_test_name(
      task_id=task_id, build_id=build_id, test_name=test_name, test_id=test_id)
  with api.step.nest('result') as presentation:
    presentation.step_text = ('task_id={0[0]} test_name={0[1]}'.format(ret))


from google.protobuf import timestamp_pb2

from recipe_engine import post_process
from PB.go.chromium.org.luci.resultdb.proto.v1 import (
    common as common_pb2,  # go/pyformat-break
    resultdb as resultdb_pb2,  #
    test_result as test_result_pb2,  #
)


def GenTests(api):
  query_test_results = resultdb_pb2.QueryTestResultsResponse(
      test_results=[
          test_result_pb2.TestResult(
              test_id='ninja://base:base_unittests/MockUnitTests.FailTest',
              name=('invocations/task-example.swarmingserver.appspot.com'
                    '-task1/result-1'),
              expected=False,
              tags=[
                  common_pb2.StringPair(
                      key="test_name", value="MockUnitTests.FailTest"),
              ],
          ),
          test_result_pb2.TestResult(
              test_id='ninja://base:base_unittests/MockUnitTests.FailTest',
              name=('invocations/task-example.swarmingserver.appspot.com'
                    '-task2/result-1'),
              expected=False,
              tags=[
                  common_pb2.StringPair(
                      key="test_name", value="MockUnitTests.FailTest"),
              ],
          ),
      ],)

  yield api.test(
      'task_id_test_name',
      api.properties(
          task_id="some-task-id",
          test_name="some_test_name",
      ),
      api.post_check(post_process.StepTextEquals, 'result',
                     'task_id=some-task-id test_name=some_test_name'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'task_id_test_id',
      api.properties(
          task_id="some-task-id",
          test_id="ninja://base:base_unittests/MockUnitTests.FailTest",
      ),
      api.resultdb.query_test_results(query_test_results),
      api.post_check(post_process.StepTextEquals, 'result',
                     'task_id=task1 test_name=MockUnitTests.FailTest'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'build_id_test_name',
      api.properties(
          build_id="build-id",
          test_name="MockUnitTests.FailTest",
      ),
      api.resultdb.query_test_results(query_test_results),
      api.post_check(post_process.StepTextEquals, 'result',
                     'task_id=task1 test_name=MockUnitTests.FailTest'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'cannot_find_test_result',
      api.properties(
          build_id="build-id",
          test_id="not-exists",
      ),
      api.resultdb.query_test_results(query_test_results),
      api.post_check(post_process.ResultReason, 'Cannot find TestResult.'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'must_have_task_id_or_build_id',
      api.properties(
          task_id=None,
          build_id=None,
          test_id="not-exists",
      ),
      api.post_check(post_process.ResultReason,
                     'Must specify task_id or build_id.'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'must_have_test_id_or_test_name',
      api.properties(
          task_id='some-task',
          test_id=None,
          test_name=None,
      ),
      api.post_check(post_process.ResultReason,
                     'Must specify test_name or test_id.'),
      api.post_process(post_process.DropExpectation),
  )
