# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'recipe_engine/assertions',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'skylab',
]

from RECIPE_MODULES.build.skylab import structs

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2
from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import (builds_service as
                                                       builds_service_pb2)
from PB.test_platform.taskstate import TaskState
from PB.test_platform.steps.execution import ExecuteResponse


def gen_skylab_req(tag):
  return structs.SkylabRequest.create(
      display_name='my_little_hwtest',
      request_tag=tag,
      suite='lacros',
      board='eve',
      cros_img='eve-release/R88-13545.0.0')


def RunSteps(api):
  hw_test_req = gen_skylab_req('m88_lacros')
  another_hw_test_req = gen_skylab_req('m87_lacros')
  build_id = api.skylab.schedule_suites('', [hw_test_req, another_hw_test_req])
  got = api.skylab.wait_on_suites(build_id, timeout_seconds=3600)
  api.assertions.assertEqual(got.status, common_pb2.SUCCESS)
  api.assertions.assertIn('m88_lacros', got.responses)
  api.assertions.assertIn('m87_lacros', got.responses)


def GenTests(api):

  def gen_tag_resp():
    case_foo = ExecuteResponse.TaskResult.TestCaseResult(
        name="foo_test_case", verdict=TaskState.VERDICT_PASSED)
    task_passed = api.skylab.gen_task_result(
        'cheets_NotificationTest',
        [case_foo],
    )
    task_failed = api.skylab.gen_task_result(
        'cheets_NotificationTest',
        [case_foo],
        verdict=TaskState.VERDICT_FAILED,
    )
    task_aborted = api.skylab.gen_task_result(
        'cheets_NotificationTest',
        [case_foo],
        life_cycle=TaskState.LIFE_CYCLE_ABORTED,
        verdict=TaskState.VERDICT_NO_VERDICT,
    )
    return {
        'm88_lacros':
            api.skylab.gen_json_execution_response(
                [task_passed, task_failed, task_aborted]),
        'm87_lacros':
            api.skylab.gen_json_execution_response(
                [task_passed, task_failed, task_aborted]),
    }

  def check_has_req_tag(check, steps, tag):
    req = api.json.loads(
        steps['schedule skylab tests.buildbucket.schedule'].logs['request'])
    properties = req['requests'][0]['scheduleBuild'].get('properties', [])
    check(tag in properties['requests'])

  yield api.test(
      'basic',
      api.buildbucket.simulated_schedule_output(
          builds_service_pb2.BatchResponse(
              responses=[dict(schedule_build=build_pb2.Build(id=1234))]),
          step_name='schedule skylab tests.buildbucket.schedule'),
      api.buildbucket.simulated_collect_output(
          [api.skylab.test_with_multi_response(1234, gen_tag_resp())],
          step_name='collect skylab results.buildbucket.collect'),
      api.post_check(check_has_req_tag, 'm88_lacros'),
      api.post_check(check_has_req_tag, 'm87_lacros'),
  )
