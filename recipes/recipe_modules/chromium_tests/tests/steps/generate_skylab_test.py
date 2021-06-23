# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import (builds_service as
                                                       builds_service_pb2)
from PB.test_platform.taskstate import TaskState
from PB.test_platform.steps.execution import ExecuteResponse

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

from recipe_engine import post_process

DEPS = [
    'build',
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/step',
    'skylab',
]


def RunSteps(api):
  with api.chromium.chromium_layout():
    builder_id, builder_config = (
        api.chromium_tests_builder_config.lookup_builder())
    return api.chromium_tests.main_waterfall_steps(builder_id, builder_config)


def GenTests(api):

  def boilerplate(skylab_gcs, tast_expr, target_name='lacros_fyi_tast_tests'):
    builder_group = 'chromium.chromiumos'
    builder = 'lacros-amd64-generic-rel'
    return sum([
        api.chromium_tests_builder_config.ci_build(
            builder_group=builder_group,
            builder=builder,
            parent_buildername='Linux Builder',
            builder_db=ctbc.BuilderDatabase.create({
                builder_group: {
                    builder:
                        ctbc.BuilderSpec.create(
                            chromium_config='chromium',
                            gclient_config='chromium',
                            skylab_gs_bucket=skylab_gcs,
                            skylab_gs_extra='lacros',
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
                        'test': target_name,
                        'timeout_sec': 7200
                    }],
                }
            }),
    ], api.empty_test_data())

  GREEN_CASE = ExecuteResponse.TaskResult.TestCaseResult(
      name='green_case', verdict=TaskState.VERDICT_PASSED)

  TASK_PASSED = api.skylab.gen_task_result(
      'tast.lacros',
      [GREEN_CASE],
  )

  TASK_NO_CASE = api.skylab.gen_task_result(
      'tast.lacros',
      [],
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
    archive_link = steps[
        'Generic Archiving Steps.gsutil upload '
        'lacros/lacros-amd64-generic-rel/571/lacros.zip'].links['gsutil.upload']
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
      boilerplate('chrome-test-builds', '("group:mainline" && "dep:lacros")'),
      simulate_ctp_response(api, 'basic_EVE_TOT', [TASK_PASSED]),
      api.post_process(post_process.StepCommandContains, 'compile', ['chrome']),
      api.post_process(archive_gsuri_should_match_skylab_req),
      api.post_process(post_process.StepTextContains, 'basic_EVE_TOT',
                       ['1 passed, 0 failed (1 total)']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'CTP response with empty test case result',
      boilerplate('chrome-test-builds', '("group:mainline" && "dep:lacros")'),
      simulate_ctp_response(api, 'basic_EVE_TOT', [TASK_NO_CASE]),
      api.post_process(post_process.StepCommandContains, 'compile', ['chrome']),
      api.post_process(archive_gsuri_should_match_skylab_req),
      api.post_process(post_process.StepFailure, 'basic_EVE_TOT'),
      api.post_process(post_process.StepTextContains, 'basic_EVE_TOT',
                       ['No test cases returned.']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'not scheduled for absent skylab gcs',
      boilerplate('', '("group:mainline" && "dep:lacros")'),
      api.post_process(
          post_process.StepTextContains, 'basic_EVE_TOT',
          ['Test was not scheduled because of absent lacros_gcs_path.']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'not scheduled for absent tast expr',
      boilerplate('chrome-test-builds', ''),
      api.post_process(
          post_process.StepTextContains, 'basic_EVE_TOT',
          ['Test was not scheduled because tast_expr was not set.']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'ci_only_test_on_ci_builder',
      api.chromium_tests_builder_config.ci_build(
          builder_group='test_group',
          builder='test_buildername',
          builder_db=ctbc.BuilderDatabase.create({
              'test_group': {
                  'test_buildername':
                      ctbc.BuilderSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                          skylab_gs_bucket='chrome-test-builds',
                          skylab_gs_extra='lacros',
                      ),
              }
          })),
      api.chromium_tests.read_source_side_spec(
          'test_group', {
              'test_buildername': {
                  'additional_compile_targets': ['chrome'],
                  'skylab_tests': [{
                      'ci_only': True,
                      'cros_board': 'eve',
                      'cros_img': 'eve-release/R89-13631.0.0',
                      'name': 'basic_EVE_TOT',
                      'tast_expr': '("group": "mainline" && "dep": "lacros")',
                      'swarming': {},
                      'test': 'basic',
                      'timeout_sec': 7200
                  }],
              }
          }),
      simulate_ctp_response(api, 'basic_EVE_TOT', [TASK_PASSED]),
      api.post_process(post_process.StepTextContains, 'basic_EVE_TOT',
                       ['1 passed, 0 failed (1 total)']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'ci_only_test_on_trybot',
      api.chromium_tests_builder_config.try_build(
          builder_group='test_group',
          builder='test_buildername',
          builder_db=ctbc.BuilderDatabase.create({
              'test_group': {
                  'test_buildername':
                      ctbc.BuilderSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                          skylab_gs_bucket='chrome-test-builds',
                          skylab_gs_extra='lacros',
                      ),
              }
          }),
          try_db=None),
      api.chromium_tests.read_source_side_spec(
          'test_group', {
              'test_buildername': {
                  'additional_compile_targets': ['chrome'],
                  'skylab_tests': [{
                      'ci_only': True,
                      'cros_board': 'eve',
                      'cros_img': 'eve-release/R89-13631.0.0',
                      'name': 'basic_EVE_TOT',
                      'tast_expr': '("group": "mainline" && "dep": "lacros")',
                      'swarming': {},
                      'test': 'basic',
                      'timeout_sec': 7200
                  }],
              }
          }),
      api.post_process(
          post_process.DoesNotRun,
          'basic_EVE_TOT',
      ),
      api.post_process(post_process.DropExpectation),
  )
