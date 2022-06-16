# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.recipe_api import Property

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'flaky_reproducer',
    'recipe_engine/step',
    'recipe_engine/json',
    'recipe_engine/properties',
]

PROPERTIES = {
    'task_id': Property(default=None, kind=str),
}


def RunSteps(api, task_id):
  with api.step.nest('get_test_binary') as presentation:
    test_binary = api.flaky_reproducer.get_test_binary(task_id)
    presentation.logs['test_binary.json'] = api.json.dumps(
        test_binary.to_jsonish(), indent=2).splitlines()


import json


def GenTests(api):
  yield api.test(
      'from_test_request',
      api.properties(task_id='54321fffffabc123'),
      api.step_data(
          'get_test_binary.get_test_binary.show request',
          api.json.output_stream(
              json.loads(
                  api.flaky_reproducer.get_test_data(
                      'gtest_task_request.json')))),
  )

  task_request = json.loads(
      api.flaky_reproducer.get_test_data('gtest_task_request.json'))
  task_request['task_slices'] = []
  yield api.test(
      'from_test_request_without_slice',
      api.properties(task_id='54321fffffabc123'),
      api.step_data('get_test_binary.get_test_binary.show request',
                    api.json.output_stream(task_request)),
      api.expect_exception(ValueError.__name__),
  )
