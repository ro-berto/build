# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

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
SHARD_COUNT = 2


def gen_skylab_req(
    tag,
    tast_expr=None,
    test_args=None,
    retries=0,
    dut_pool='',
    secondary_board='',
    secondary_cros_img='',
    bucket='',
    autotest_name='',
    tast_expr_file='',
    benchmark='',
    results_label='',
    story_filter='',
    test_shard_map_filename='',
    telemetry_shard_index=None,
    shards=1,
):
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
      bucket=bucket,
      autotest_name=autotest_name,
      resultdb=ResultDB.create(**RESULTDB_CONFIG),
      benchmark=benchmark,
      results_label=results_label,
      story_filter=story_filter,
      test_shard_map_filename=test_shard_map_filename,
      telemetry_shard_index=telemetry_shard_index,
      shards=shards,
  )


REQUESTS = [
    gen_skylab_req(
        'm88_tast_with_retry',
        tast_expr=LACROS_TAST_EXPR,
        retries=3,
        bucket='a_different_chromium_bucket'),
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
        autotest_name='tast.nearby-share'),
    gen_skylab_req(
        'telemetry_test_args',
        tast_expr=None,
        benchmark='speedometer2',
        story_filter='Speedometer2',
        results_label='12345',
        test_shard_map_filename='per_map.json',
        telemetry_shard_index=0),
    gen_skylab_req(
        'sharded_tast_req',
        tast_expr=LACROS_TAST_EXPR,
        dut_pool='cross_device_multi_cb',
        tast_expr_file='tast_expr_file.filter',
        shards=SHARD_COUNT),
]


def RunSteps(api):
  build_ids = api.skylab.schedule_suites(REQUESTS)
  api.skylab.wait_on_suites(build_ids, timeout_seconds=3600)

def GenTests(api):

  def test_args_for_shard(shard):
    return 'resultdb_settings=eyJhcnRpZmFjdF9kaXJlY3RvcnkiOiAiJHtJU09MQVRFRF9P'\
        'VVRESVJ9IiwgImNvZXJjZV9uZWdhdGl2ZV9kdXJhdGlvbiI6IHRydWUsICJlbmFibGUiO'\
        'iB0cnVlLCAiZXhvbmVyYXRlX3VuZXhwZWN0ZWRfcGFzcyI6IHRydWUsICJoYXNfbmF0aX'\
        'ZlX3Jlc3VsdGRiX2ludGVncmF0aW9uIjogZmFsc2UsICJpbmNsdWRlIjogZmFsc2UsICJ'\
        'yZXN1bHRfYWRhcHRlcl9wYXRoIjogInJlc3VsdF9hZGFwdGVyIiwgInJlc3VsdF9maWxl'\
        'IjogIm91dHB1dC5qc29uIiwgInJlc3VsdF9mb3JtYXQiOiAiZ3Rlc3QiLCAidGVzdF9pZ'\
        'F9hc190ZXN0X2xvY2F0aW9uIjogZmFsc2V9 tast_expr_b64=KCJncm91cDptYWlubGl'\
        'uZSIgJiYgImRlcDpsYWNyb3MiICYmICIhaW5mb3JtYXRpb25hbCIp '\
        'exe_rel_path=out/Release/bin/run_foo_unittest '\
        'tast_expr_file=tast_expr_file.filter '\
        'tast_expr_key=default shard_index={} '\
        'total_shards={}'.format(shard, SHARD_COUNT)

  yield api.test(
      'basic',
      api.post_process(
          post_process.StepCommandContains,
          'schedule skylab tests.' + REQUESTS[0].request_tag + '.schedule', [
              'run', 'test', '-json', '-board', 'eve', '-bucket',
              'a_different_chromium_bucket', '-pool', 'DUT_POOL_QUOTA',
              '-image', 'eve-release/R88-13545.0.0', '-timeout-mins', '60',
              '-qs-account', 'lacros', '-max-retries', '3'
          ]),
      api.skylab.mock_wait_on_suites('find test runner build', len(REQUESTS)),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'fail_request_continues',
      api.step_data(
          'schedule skylab tests.' + REQUESTS[0].request_tag + '.schedule',
          retcode=1),
      api.post_process(post_process.StepFailure, 'schedule skylab tests'),
      api.post_process(
          post_process.StepCommandContains,
          'schedule skylab tests.' + REQUESTS[2].request_tag + '.schedule', [
              'run', 'test', '-json', '-board', 'eve', '-pool',
              'cross_device_multi_cb', '-image', 'eve-release/R88-13545.0.0',
              '-timeout-mins', '60', '-qs-account', 'lacros'
          ]),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'multiple_shards_trigger',
      api.step_data(
          'schedule skylab tests.' + REQUESTS[0].request_tag + '.schedule',
          retcode=1),
      api.post_process(post_process.StepFailure, 'schedule skylab tests'),
      api.post_process(
          post_process.MustRun,
          'schedule skylab tests.{0}.schedule'.format(REQUESTS[5].request_tag)),
      api.post_process(
          post_process.MustRun, 'schedule skylab tests.{0}.schedule (1)'.format(
              REQUESTS[5].request_tag)),
      api.post_process(
          post_process.StepCommandContains,
          'schedule skylab tests.' + REQUESTS[5].request_tag + '.schedule',
          [test_args_for_shard(0)]),
      api.post_process(
          post_process.StepCommandContains,
          'schedule skylab tests.' + REQUESTS[5].request_tag + '.schedule (1)',
          [test_args_for_shard(1)]),
      api.post_process(post_process.DropExpectation),
  )
