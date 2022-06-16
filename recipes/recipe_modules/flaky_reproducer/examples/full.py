# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.recipe_api import Property

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'flaky_reproducer',
    'recipe_engine/json',
    'recipe_engine/raw_io',
    'recipe_engine/swarming',
    'recipe_engine/properties',
]

PROPERTIES = {
    'task_id': Property(default=None, kind=str),
    'test_name': Property(default=None, kind=str),
}


def RunSteps(api, task_id, test_name):
  api.flaky_reproducer.run(task_id, test_name)


from recipe_engine.post_process import (DropExpectation, StatusFailure,
                                        ResultReason)


def GenTests(api):
  yield api.test(
      'happy_path',
      api.properties(task_id='54321fffffabc123', test_name='foo.bar'),
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
  )

  yield api.test(
      'no_exists_task_result',
      api.properties(task_id='54321fffffabc123', test_name='foo.bar'),
      api.step_data('get_test_result_summary.swarming collect',
                    api.swarming.collect([])),
      api.post_process(StatusFailure),
      api.post_process(ResultReason,
                       'Cannot find TaskResult for task 54321fffffabc123.'),
      api.post_process(DropExpectation),
  )

  yield api.test(
      'not_supported_task_result',
      api.properties(task_id='54321fffffabc123', test_name='foo.bar'),
      api.step_data('get_test_result_summary.download swarming outputs',
                    api.raw_io.output_dir({})),
      api.post_process(StatusFailure),
      api.post_process(ResultReason, 'Not supported task result.'),
      api.post_process(DropExpectation),
  )
