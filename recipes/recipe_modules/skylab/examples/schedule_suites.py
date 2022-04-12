# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'skylab',
]

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
                   autotest_name='',
                   tast_expr_file=''):
  return SkylabRequest.create(
      request_tag=tag,
      board='eve',
      tast_expr=tast_expr,
      tast_expr_file=tast_expr_file,
      tast_expr_key='default',
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
        dut_pool='cross_device_multi_cb',
        tast_expr_file='tast_expr_file.filter'),
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

  yield api.test(
      'basic',
      api.post_process(
          post_process.StepCommandContains,
          'schedule skylab tests.' + REQUESTS[0].request_tag + '.schedule', [
              'run', 'test', '-json', '-board', 'eve', '-pool',
              'DUT_POOL_QUOTA', '-image', 'eve-release/R88-13545.0.0',
              '-timeout-mins', '60', '-qs-account', 'lacros', '-max-retries',
              '3'
          ]),
      api.skylab.wait_on_suites('find test runner build', len(REQUESTS)),
      api.post_process(post_process.DropExpectation),
  )
