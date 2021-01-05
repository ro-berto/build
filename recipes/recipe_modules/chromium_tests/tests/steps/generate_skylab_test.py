# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'build',
    'chromium',
    'chromium_tests',
    'recipe_engine/buildbucket',
    'recipe_engine/platform',
    'recipe_engine/step',
    'skylab',
]

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2
from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import (builds_service as
                                                       builds_service_pb2)
from PB.test_platform.taskstate import TaskState
from PB.test_platform.steps.execution import ExecuteResponse

from recipe_engine import post_process


def RunSteps(api):
  with api.chromium.chromium_layout():
    return api.chromium_tests.main_waterfall_steps()


def GenTests(api):

  def boilerplate():
    builder_group = 'chromium.fyi'
    builder = 'chromeos-amd64-generic-lacros-rel'
    return sum([
        api.chromium.ci_build(
            builder_group=builder_group,
            builder=builder,
            parent_buildername='Linux Builder'),
        api.platform('linux', 64),
        api.chromium_tests.read_source_side_spec(
            builder_group, {
                builder: {
                    'additional_compile_targets': ['chrome'],
                    'skylab_tests': [{
                        'cros_board': 'eve',
                        'cros_img': 'eve-release/R89-13631.0.0',
                        'name': 'basic_EVE_TOT',
                        'suite': 'lacros-basic',
                        'swarming': {},
                        'test': 'basic',
                        'timeout': 3600
                    }],
                }
            }),
    ], api.empty_test_data())

  GREEN_CASE = ExecuteResponse.TaskResult.TestCaseResult(
      name='green_case', verdict=TaskState.VERDICT_PASSED)

  RED_CASE = ExecuteResponse.TaskResult.TestCaseResult(
      name='red_case', verdict=TaskState.VERDICT_FAILED)

  TASK_PASSED = api.skylab.gen_task_result(
      'cheets_NotificationTest',
      [GREEN_CASE],
  )

  TASK_FAILED = api.skylab.gen_task_result(
      'cheets_NotificationTest',
      [GREEN_CASE, RED_CASE],
      verdict=TaskState.VERDICT_FAILED,
  )

  def gen_tag_resp(api, tag, tasks):
    return {
        tag: api.skylab.gen_json_execution_response(tasks),
    }

  def simulate_ctp_response(api, tag, task):
    test_data = api.buildbucket.simulated_schedule_output(
        builds_service_pb2.BatchResponse(
            responses=[dict(schedule_build=build_pb2.Build(id=1234))]),
        step_name=(
            'test_pre_run.schedule tests on skylab.buildbucket.schedule'))
    test_data += api.buildbucket.simulated_collect_output(
        [
            api.skylab.test_with_multi_response(1234,
                                                gen_tag_resp(api, tag, task)),
        ],
        step_name='collect skylab results.buildbucket.collect')
    return test_data

  yield api.test(
      'basic',
      boilerplate(),
      simulate_ctp_response(api, 'basic_EVE_TOT', [TASK_PASSED, TASK_FAILED]),
      api.post_process(post_process.StepCommandContains, 'compile', ['chrome']),
      api.post_process(post_process.StepTextContains,
                       'basic_EVE_TOT.attempt: #1',
                       ['1 passed, 0 failed (1 total)']),
      api.post_process(post_process.StepTextContains,
                       'basic_EVE_TOT.attempt: #2',
                       ['1 passed, 1 failed (2 total)']),
  )
