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
  api.flaky_reproducer.run(task_id, test_name)


from recipe_engine.post_process import (DropExpectation, StatusFailure,
                                        ResultReason)


def GenTests(api):
  success_swarming_result = api.swarming.task_result(
      id='0',
      name='flaky reproducer strategy repeat for MockUnitTests.FailTest',
      state=api.swarming.TaskState.COMPLETED,
      output='some-output',
      outputs=('reproducing_step.json',))
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
          'get_test_binary.show request',
          api.json.output_stream(
              api.json.loads(
                  api.flaky_reproducer.get_test_data(
                      'gtest_task_request.json')))),
      api.step_data('collect strategy results',
                    api.swarming.collect([success_swarming_result])),
      api.step_data(
          'load ReproducingStep',
          api.file.read_json(
              api.json.loads(
                  api.flaky_reproducer.get_test_data(
                      'reproducing_step.json')))),
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
          'get_test_binary.show request',
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
