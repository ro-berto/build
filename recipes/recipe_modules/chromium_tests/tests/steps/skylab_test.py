# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from google.protobuf import json_format

from RECIPE_MODULES.build.chromium_tests import steps

from recipe_engine.post_process import StepException

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2
from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import (builds_service as
                                                       builds_service_pb2)

from PB.test_platform.taskstate import TaskState
from PB.test_platform.steps.execution import ExecuteResponse

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
    'skylab',
    'test_utils',
]


def RunSteps(api):
  api.chromium.set_config('chromium')
  test_spec = steps.SkylabTestSpec.create(
      name=api.properties.get('test_name', 'EVE_TOT'),
      target_name='lacros_fyi_tast_tests',
      tast_expr='lacros.Basic',
      cros_board='eve',
      cros_img='eve-release/R88-13545.0.0')
  test = test_spec.get_test()
  test.lacros_gcs_path = 'lacros'
  test.exe_rel_path = 'out/Release/chrome'
  api.test_utils.run_tests(api.chromium_tests.m, [test], 'with patch')
  api.step('details', [])
  api.step.active_result.presentation.logs['details'] = [
      'compile_targets: {!r}'.format(test.compile_targets()),
  ]


def GenTests(api):

  GREEN_CASE = ExecuteResponse.TaskResult.TestCaseResult(
      name="green_case", verdict=TaskState.VERDICT_PASSED)

  RED_CASE = ExecuteResponse.TaskResult.TestCaseResult(
      name="red_case", verdict=TaskState.VERDICT_FAILED)

  TASK_PASSED = api.skylab.gen_task_result(
      'cheets_NotificationTest',
      [GREEN_CASE],
  )

  TASK_FAILED = api.skylab.gen_task_result(
      'cheets_NotificationTest',
      [RED_CASE],
      verdict=TaskState.VERDICT_FAILED,
  )

  TASK_ABORTED = api.skylab.gen_task_result(
      'cheets_NotificationTest',
      [],
      life_cycle=TaskState.LIFE_CYCLE_ABORTED,
      verdict=TaskState.VERDICT_NO_VERDICT,
  )

  def gen_tag_resp(api, tag, task):
    return {
        tag: api.skylab.gen_json_execution_response([task]),
    }

  def simulate_ctp_response(api, tag, task):
    test_data = api.buildbucket.simulated_schedule_output(
        builds_service_pb2.BatchResponse(
            responses=[dict(schedule_build=build_pb2.Build(id=1234))]),
        step_name=('test_pre_run (with patch).schedule tests on '
                   'skylab.buildbucket.schedule'))
    test_data += api.buildbucket.simulated_collect_output(
        [
            api.skylab.test_with_multi_response(1234,
                                                gen_tag_resp(api, tag, task)),
        ],
        step_name='collect skylab results.buildbucket.collect')
    return test_data

  yield api.test(
      'passed',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      simulate_ctp_response(api, 'EVE_TOT', TASK_PASSED),
  )

  yield api.test(
      'failed',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      simulate_ctp_response(api, 'EVE_TOT', TASK_FAILED),
  )

  yield api.test(
      'aborted',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      simulate_ctp_response(api, 'EVE_TOT', TASK_ABORTED),
  )

  yield api.test(
      'infra_failure',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.buildbucket.simulated_schedule_output(
          builds_service_pb2.BatchResponse(
              responses=[dict(schedule_build=build_pb2.Build(id=1234))]),
          step_name=('test_pre_run (with patch).schedule tests on '
                     'skylab.buildbucket.schedule')),
      api.step_data(
          'collect skylab results.buildbucket.collect.wait',
          api.json.output(json_format.MessageToJson(build_pb2.Build(id=0))),
          retcode=1),
      api.buildbucket.simulated_get(
          build_pb2.Build(id=1234, status=common_pb2.INFRA_FAILURE),
          step_name='collect skylab results.buildbucket.get'),
      api.post_process(StepException, 'collect skylab results'),
  )
