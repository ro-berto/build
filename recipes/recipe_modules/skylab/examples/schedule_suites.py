# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'recipe_engine/assertions',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'skylab',
]

import re
import base64

from RECIPE_MODULES.build.chromium_tests.resultdb import ResultDB
from RECIPE_MODULES.build.skylab.structs import SkylabRequest

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2
from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import (builds_service as
                                                       builds_service_pb2)
from PB.test_platform.taskstate import TaskState
from PB.test_platform.steps.execution import ExecuteResponse

from recipe_engine import post_process

LACROS_TAST_EXPR = '("group:mainline" && "dep:lacros" && "!informational")'
LACROS_GTEST_ARGS = '--gtest_filter="VaapiTest.*"'
RESULTDB_CONFIG = {
    'result_file': 'output.json',
    'result_format': 'gtest',
}


def gen_skylab_req(tag, tast_expr=None, test_args=None, dut_pool=''):
  return SkylabRequest.create(
      request_tag=tag,
      board='eve',
      tast_expr=tast_expr,
      test_args=test_args,
      lacros_gcs_path='gs://fake_bucket/lacros.zip',
      exe_rel_path='out/Release/bin/run_foo_unittest',
      cros_img='eve-release/R88-13545.0.0',
      dut_pool=dut_pool,
      resultdb=ResultDB.create(**RESULTDB_CONFIG))


def RunSteps(api):
  hw_test_req = gen_skylab_req('m88_lacros', tast_expr=LACROS_TAST_EXPR)
  another_hw_test_req = gen_skylab_req('m87_lacros', tast_expr=LACROS_TAST_EXPR)
  gtest_req = gen_skylab_req(
      'm88_urlunittest', tast_expr=None, test_args=LACROS_GTEST_ARGS)
  nearby_connection_req = gen_skylab_req(
      'm87_nearby',
      tast_expr=LACROS_TAST_EXPR,
      dut_pool='cross_device_multi_cb')
  build_id = api.skylab.schedule_suites(
      '', [hw_test_req, another_hw_test_req, gtest_req, nearby_connection_req])
  got = api.skylab.wait_on_suites(build_id, timeout_seconds=3600)
  api.assertions.assertEqual(got.status, common_pb2.SUCCESS)
  api.assertions.assertIn('m88_lacros', got.responses)
  api.assertions.assertEqual(len(got.responses.get('m88_lacros')), 3)
  api.assertions.assertIn('m87_lacros', got.responses)
  api.assertions.assertEqual(len(got.responses.get('m87_lacros')), 3)


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
        'm88_urlunittest':
            api.skylab.gen_json_execution_response(
                [task_passed, task_failed, task_aborted]),
        'm87_nearby':
            api.skylab.gen_json_execution_response(
                [task_passed, task_failed, task_aborted]),
    }

  def _args_to_dict(arg_line):
    arg_re = re.compile(r'(\w+)[:=](.*)$')
    args_dict = {}
    for arg in arg_line.split(' '):
      match = arg_re.match(arg)
      if match:
        args_dict[match.group(1).lower()] = match.group(2)
    return args_dict

  def check_has_req_tag(check, steps, tag):
    req = api.json.loads(
        steps['schedule skylab tests.buildbucket.schedule'].logs['request'])
    properties = req['requests'][0]['scheduleBuild'].get('properties', [])
    check(tag in properties['requests'])

  def check_pool(check, steps, tag, pool='', managed=False):
    req = api.json.loads(
        steps['schedule skylab tests.buildbucket.schedule'].logs['request'])
    properties = req['requests'][0]['scheduleBuild'].get('properties', [])
    scheduling = properties['requests'][tag]['params']['scheduling']
    if managed:
      check(scheduling['managedPool'] == 'MANAGED_POOL_QUOTA')
    else:
      check(scheduling['unmanagedPool'] == pool)

  def check_test_arg(check, steps, lacros_gcs_path, tast_expr, test_args):
    req = api.json.loads(
        steps['schedule skylab tests.buildbucket.schedule'].logs['request'])
    properties = req['requests'][0]['scheduleBuild'].get('properties', [])
    for req in properties['requests'].values():
      test = req['testPlan']['test'][0]
      got = _args_to_dict(test['autotest']['testArgs'])
      if got.get('tast_expr_b64'):
        check(tast_expr == base64.b64decode(got['tast_expr_b64']))
      else:
        check(test_args == base64.b64decode(got['test_args_b64']))
      sw_deps = req['params']['softwareDependencies']
      dep_of_lacros = [
          d['lacrosGcsPath'] for d in sw_deps if d.get('lacrosGcsPath')
      ]
      check(lacros_gcs_path in dep_of_lacros)
      if got.get('resultdb_settings'):
        rdb_config = api.json.loads(
            base64.b64decode(got.get('resultdb_settings')))
        check(all([rdb_config[k] == v for k, v in RESULTDB_CONFIG.items()]))

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
      api.post_check(check_pool, 'm88_lacros', managed=True),
      api.post_check(check_has_req_tag, 'm87_lacros'),
      api.post_check(check_has_req_tag, 'm88_urlunittest'),
      api.post_check(check_has_req_tag, 'm87_nearby'),
      api.post_check(check_pool, 'm87_nearby', 'cross_device_multi_cb'),
      api.post_check(check_test_arg, 'gs://fake_bucket/lacros.zip',
                     LACROS_TAST_EXPR, LACROS_GTEST_ARGS),
      api.post_process(post_process.DropExpectation),
  )
