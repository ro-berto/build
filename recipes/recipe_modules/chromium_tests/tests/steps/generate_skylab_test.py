# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import (builds_service as
                                                       builds_service_pb2)
from PB.test_platform.taskstate import TaskState
from PB.test_platform.steps.execution import ExecuteResponse

from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec

from recipe_engine import post_process

DEPS = [
    'build',
    'chromium',
    'chromium_tests',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/step',
    'skylab',
]


def RunSteps(api):
  with api.chromium.chromium_layout():
    return api.chromium_tests.main_waterfall_steps()


def GenTests(api):

  def boilerplate(skylab_gcs, tast_expr):
    builder_group = 'chromium.chromiumos'
    builder = 'lacros-amd64-generic-rel'
    return sum([
        api.chromium.ci_build(
            builder_group=builder_group,
            builder=builder,
            parent_buildername='Linux Builder',
        ),
        api.platform('linux', 64),
        api.chromium_tests.builders(
            bot_db.BotDatabase.create({
                builder_group: {
                    builder:
                        bot_spec.BotSpec.create(
                            chromium_config='chromium',
                            gclient_config='chromium',
                            skylab_gs_bucket=skylab_gcs,
                        ),
                }
            })),
        api.chromium_tests.read_source_side_spec(
            builder_group, {
                builder: {
                    'additional_compile_targets': ['chrome'],
                    'skylab_tests': [{
                        'cros_board': 'eve',
                        'cros_img': 'eve-release/R89-13631.0.0',
                        'name': 'basic_EVE_TOT',
                        'tast_expr': tast_expr,
                        'swarming': {},
                        'test': 'basic',
                        'timeout_sec': 7200
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

  def archive_gsuri_should_match_skylab_req(check, steps):
    archive_link = steps['Generic Archiving Steps.gsutil upload'].links[
        'gsutil.upload']
    gs_uri = archive_link.replace('https://storage.cloud.google.com/', 'gs://')
    build_req = api.json.loads(
        steps['test_pre_run.schedule tests on skylab.buildbucket.schedule']
        .logs['request'])
    properties = build_req['requests'][0]['scheduleBuild'].get('properties', [])
    for req in properties['requests'].values():
      test = req['testPlan']['test'][0]
      check(gs_uri in test['autotest']['testArgs'])

  yield api.test(
      'basic',
      boilerplate('lacros', '("group:mainline" && "dep:lacros")'),
      simulate_ctp_response(api, 'basic_EVE_TOT', [TASK_PASSED, TASK_FAILED]),
      api.post_process(post_process.StepCommandContains, 'compile', ['chrome']),
      api.post_process(archive_gsuri_should_match_skylab_req),
      api.post_process(post_process.StepTextContains,
                       'basic_EVE_TOT.attempt: #1',
                       ['1 passed, 0 failed (1 total)']),
      api.post_process(post_process.StepTextContains,
                       'basic_EVE_TOT.attempt: #2',
                       ['1 passed, 1 failed (2 total)']),
  )

  yield api.test(
      'not scheduled for absent skylab gcs',
      boilerplate('', '("group:mainline" && "dep:lacros")'),
      api.post_process(
          post_process.StepTextContains, 'basic_EVE_TOT',
          ['Test was not scheduled because of absent lacros_gcs_path.']),
  )

  yield api.test(
      'not scheduled for absent tast expr',
      boilerplate('lacros', ''),
      api.post_process(
          post_process.StepTextContains, 'basic_EVE_TOT',
          ['Test was not scheduled because tast_expr was not set.']),
  )
