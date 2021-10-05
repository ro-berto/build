# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
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
LACROS_GCS_PATH = 'gs://fake_bucket/lacros.squashfs'
RESULTDB_CONFIG = {
    'result_file': 'output.json',
    'result_format': 'gtest',
}


def gen_skylab_req(tag, tast_expr=None, test_args=None, retries=0, dut_pool=''):
  return SkylabRequest.create(
      request_tag=tag,
      board='eve',
      tast_expr=tast_expr,
      test_args=test_args,
      lacros_gcs_path=LACROS_GCS_PATH,
      exe_rel_path='out/Release/bin/run_foo_unittest',
      cros_img='eve-release/R88-13545.0.0',
      dut_pool=dut_pool,
      retries=retries,
      resultdb=ResultDB.create(**RESULTDB_CONFIG))


REQUESTS = [
    gen_skylab_req(
        'm88_tast_with_retry', tast_expr=LACROS_TAST_EXPR, retries=3),
    gen_skylab_req(
        'm88_gtest_test_args', tast_expr=None, test_args=LACROS_GTEST_ARGS),
    gen_skylab_req(
        'm88_nearby_dut_pool',
        tast_expr=LACROS_TAST_EXPR,
        dut_pool='cross_device_multi_cb')
]


def RunSteps(api):
  build_ids = api.skylab.schedule_suites(REQUESTS)
  api.skylab.wait_on_suites(build_ids, timeout_seconds=3600)


def GenTests(api):

  def _extract_ctp_requests(steps):
    return api.skylab.step_logs_to_ctp_by_tag(
        steps['schedule skylab tests.buildbucket.schedule'].logs)

  def _args_to_dict(arg_line):
    arg_re = re.compile(r'(\w+)[:=](.*)$')
    args_dict = {}
    for arg in arg_line.split(' '):
      match = arg_re.match(arg)
      if match:
        args_dict[match.group(1).lower()] = match.group(2)
    return args_dict

  def check_req_has_enable_retry(check, steps, tag, retries):
    """CTP request we created should have retry enabled."""
    ctp_reqs = _extract_ctp_requests(steps)
    check(ctp_reqs[tag]['params']['retry']['allow'])
    check(ctp_reqs[tag]['params']['retry']['max'] == retries)

  def check_has_req_tags(check, steps, requests):
    """Request tag should exist in the CTP requests."""
    ctp_reqs = _extract_ctp_requests(steps)
    for r in requests:
      check(r.request_tag in ctp_reqs)

  def check_pool(check, steps, tag, pool='', managed=False):
    """CTP request should have the expected pool."""
    ctp_reqs = _extract_ctp_requests(steps)
    scheduling = ctp_reqs[tag]['params']['scheduling']
    if managed:
      check(scheduling['managedPool'] == 'MANAGED_POOL_QUOTA')
    else:
      check(scheduling['unmanagedPool'] == pool)

  def check_test_arg(check,
                     steps,
                     tag,
                     lacros_gcs_path=LACROS_GCS_PATH,
                     tast_expr=LACROS_TAST_EXPR,
                     test_args=LACROS_GTEST_ARGS):
    """CTP request should have expected parameters in the test args."""
    ctp_reqs = _extract_ctp_requests(steps)
    sw_deps = ctp_reqs[tag]['params']['softwareDependencies']
    dep_of_lacros = [
        d['lacrosGcsPath'] for d in sw_deps if d.get('lacrosGcsPath')
    ]
    check(lacros_gcs_path in dep_of_lacros)
    test = ctp_reqs[tag]['testPlan']['test'][0]
    got = _args_to_dict(test['autotest']['testArgs'])
    if got.get('tast_expr_b64'):
      check(tast_expr == base64.b64decode(got['tast_expr_b64']))
    else:
      check(test_args == base64.b64decode(got['test_args_b64']))

    if got.get('resultdb_settings'):
      rdb_config = api.json.loads(
          base64.b64decode(got.get('resultdb_settings')))
      check(all([rdb_config[k] == v for k, v in RESULTDB_CONFIG.items()]))

  def gen_tag_resps():
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
    return [
        {
            'm88_tast_with_retry':
                api.skylab.gen_json_execution_response(
                    [task_passed, task_failed, task_aborted])
        },
        {
            'm88_gtest_test_args':
                api.skylab.gen_json_execution_response(
                    [task_passed, task_failed, task_aborted])
        },
        {
            'm88_nearby_dut_pool':
                api.skylab.gen_json_execution_response(
                    [task_passed, task_failed, task_aborted])
        },
    ]

  yield api.test(
      'basic',
      api.skylab.gen_schedule_build_resps('schedule skylab tests',
                                          len(REQUESTS)),
      api.buildbucket.simulated_collect_output(
          api.skylab.test_with_multi_response(1234, gen_tag_resps()),
          step_name='collect skylab results.buildbucket.collect'),
      api.post_check(check_has_req_tags, REQUESTS),
      api.post_check(check_req_has_enable_retry, 'm88_tast_with_retry', 3),
      api.post_check(check_pool, 'm88_gtest_test_args', managed=True),
      api.post_check(check_pool, 'm88_nearby_dut_pool',
                     'cross_device_multi_cb'),
      api.post_check(check_test_arg, 'm88_gtest_test_args'),
      api.post_check(check_test_arg, 'm88_tast_with_retry'),
      api.post_process(post_process.DropExpectation),
  )
