# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'skylab',
]

import re
import base64

from RECIPE_MODULES.build.chromium_tests.resultdb import ResultDB
from RECIPE_MODULES.build.skylab.structs import SkylabRequest

from recipe_engine import post_process

LACROS_TAST_EXPR = '("group:mainline" && "dep:lacros" && "!informational")'
LACROS_GTEST_ARGS = '--gtest_filter="VaapiTest.*"'
LACROS_GCS_PATH = 'gs://fake_bucket/lacros.squashfs'
RESULTDB_CONFIG = {
    'result_file': 'output.json',
    'result_format': 'gtest',
}


def gen_skylab_req(tag,
                   tast_expr=None,
                   test_args=None,
                   retries=0,
                   dut_pool='',
                   secondary_board='',
                   secondary_cros_img='',
                   autotest_name=''):
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
      secondary_board=secondary_board,
      secondary_cros_img=secondary_cros_img,
      autotest_name=autotest_name,
      resultdb=ResultDB.create(**RESULTDB_CONFIG))


REQUESTS = [
    gen_skylab_req(
        'm88_tast_with_retry', tast_expr=LACROS_TAST_EXPR, retries=3),
    gen_skylab_req(
        'm88_gtest_test_args', tast_expr=None, test_args=LACROS_GTEST_ARGS),
    gen_skylab_req(
        'm88_nearby_dut_pool',
        tast_expr=LACROS_TAST_EXPR,
        dut_pool='cross_device_multi_cb'),
    gen_skylab_req(
        'm88_nearby_multi_dut',
        secondary_board='eve',
        secondary_cros_img='eve-release/R88-13545.0.0',
        tast_expr=LACROS_TAST_EXPR,
        autotest_name='tast.nearby-share')
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

  def _decode_b64_str(s):
    return base64.b64decode(s).decode('utf-8')

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
    decoded_test_args_b64 = _decode_b64_str(got['test_args_b64'])
    check(test_args == decoded_test_args_b64)

    if got.get('resultdb_settings'):
      rdb_config = api.json.loads(
          base64.b64decode(got.get('resultdb_settings')))
      check(all([rdb_config[k] == v for k, v in RESULTDB_CONFIG.items()]))

  def check_secondary_device(check,
                             steps,
                             tag,
                             secondary_board,
                             secondary_cros_img,
                             lacros_gcs_path=LACROS_GCS_PATH):
    ctp_reqs = _extract_ctp_requests(steps)
    secondary_device = ctp_reqs[tag]['params']['secondaryDevices'][0]
    secondary_sw_dep = secondary_device['softwareDependencies']
    dep_of_lacros = [
        d['lacrosGcsPath'] for d in secondary_sw_dep if d.get('lacrosGcsPath')
    ]
    check(lacros_gcs_path in dep_of_lacros)
    chromeos_build = [
        d['chromeosBuild'] for d in secondary_sw_dep if d.get('chromeosBuild')
    ]
    check(secondary_cros_img in chromeos_build)
    check(secondary_device["softwareAttributes"]["buildTarget"]["name"] ==
          secondary_board)

  yield api.test(
      'basic',
      api.skylab.gen_schedule_build_resps('schedule skylab tests',
                                          len(REQUESTS)),
      api.skylab.wait_on_suites('find test runner build', len(REQUESTS)),
      api.post_check(check_has_req_tags, REQUESTS),
      api.post_check(check_req_has_enable_retry, 'm88_tast_with_retry', 3),
      api.post_check(check_pool, 'm88_gtest_test_args', managed=True),
      api.post_check(check_pool, 'm88_nearby_dut_pool',
                     'cross_device_multi_cb'),
      api.post_check(check_test_arg, 'm88_gtest_test_args'),
      api.post_check(check_secondary_device, 'm88_nearby_multi_dut', 'eve',
                     'eve-release/R88-13545.0.0'),
      api.post_process(post_process.DropExpectation),
  )
