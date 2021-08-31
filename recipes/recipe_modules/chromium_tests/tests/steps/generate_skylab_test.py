# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import itertools
import json

from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import (builds_service as
                                                       builds_service_pb2)
from PB.go.chromium.org.luci.resultdb.proto.v1 import (invocation as
                                                       invocation_pb2)

from PB.test_platform.taskstate import TaskState
from PB.test_platform.steps.execution import ExecuteResponse

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

from recipe_engine import post_process

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
    'filter',
    'skylab',
    'test_utils',
    'depot_tools/tryserver',
    'recipe_engine/buildbucket',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/json',
    'recipe_engine/resultdb',
    'recipe_engine/step',
]


def RunSteps(api):
  builder_id, builder_config = (
      api.chromium_tests_builder_config.lookup_builder())
  if api.tryserver.is_tryserver:
    return api.chromium_tests.trybot_steps(builder_id, builder_config)
  else:
    return api.chromium_tests.main_waterfall_steps(builder_id, builder_config)



def GenTests(api):

  TAST_TARGET = 'lacros_fyi_tast_tests'
  GTEST_TARGET = 'vaapi_unittest'

  GOOD_ISOLATE_TEXT = """
    {'variables': {'command': ['bin/run_lacros_smoke_tast_tests',
                            '--logs-dir=${ISOLATED_OUTDIR}'],
                'files': ['../../.vpython',
                          'bin/run_vaapi_unittest',
                          'resources.pak',
                          'resources.pak.info',
                          './chrome',
                          '../../testing/buildbot/filters',
                          'gen/third_party',
                          '../../testing/buildbot/filters',
                            ]}}
  """

  EMPTY_FILE_LIST = """
    {'variables': {'command': ['bin/run_lacros_smoke_tast_tests',
                            '--logs-dir=${ISOLATED_OUTDIR}'],
                'files': []}}
  """

  BAD_ISOLATE_TEXT = """
    not isolate file at all
  """

  def boilerplate(skylab_gcs,
                  tast_expr='',
                  test_args='',
                  isolate_content=GOOD_ISOLATE_TEXT,
                  isolate_file_exists=True,
                  is_ci_build=True,
                  target_name=TAST_TARGET,
                  should_read_isolate=True):
    builder_group = 'chromium.chromiumos'
    builder = 'lacros-amd64-generic-rel'
    builder_db = ctbc.BuilderDatabase.create({
        builder_group: {
            builder:
                ctbc.BuilderSpec.create(
                    chromium_config='chromium',
                    gclient_config='chromium',
                    skylab_gs_bucket=skylab_gcs,
                    skylab_gs_extra='lacros',
                ),
        }
    })
    if is_ci_build:
      build_gen = api.chromium_tests_builder_config.ci_build(
          builder_group=builder_group,
          builder=builder,
          parent_buildername='Linux Builder',
          builder_db=builder_db,
      )
    else:
      build_gen = api.chromium_tests_builder_config.try_build(
          builder_group=builder_group,
          builder=builder,
          builder_db=builder_db,
          try_db=None,
      )
      build_gen += api.filter.suppress_analyze()

    steps = sum([
        build_gen,
        api.chromium_tests.read_source_side_spec(
            builder_group, {
                builder: {
                    'skylab_tests': [{
                        'cros_board':
                            'eve',
                        'cros_img':
                            'eve-release/R89-13631.0.0',
                        'test_id_prefix':
                            'ninja://chromeos/lacros:lacros_fyi_tast_tests/',
                        'ci_only':
                            True,
                        'name':
                            'basic_EVE_TOT',
                        'tast_expr':
                            tast_expr,
                        'args': [test_args],
                        'swarming': {},
                        'test':
                            target_name,
                        'resultdb': {
                            'enable': True,
                        },
                        'timeout_sec':
                            7200
                    }],
                }
            }),
    ], api.empty_test_data())
    # Mock the file/folder for recipe training.
    mock_paths = [
        api.path['start_dir'].join('squashfs', 'squashfs-tools', 'mksquashfs')
    ]
    # testing/buildbot/filters should be a folder.
    mock_paths.append(api.path['checkout'].join('testing', 'buildbot',
                                                'filters', 'foo'))
    mock_paths.append(api.path['checkout'].join('out', 'Release', 'chrome'))
    mock_paths.append(api.path['checkout'].join('out', 'Release', 'bin',
                                                'run_%s' % target_name))
    if isolate_file_exists:
      mock_paths.append(api.path['checkout'].join('out', 'Release',
                                                  '%s.isolate' % target_name))
    steps += api.path.exists(*mock_paths)
    if isolate_file_exists and should_read_isolate:
      steps += api.step_data(
          'prepare skylab tests.'
          'collect runtime deps for %s.read isolate file' % target_name,
          api.file.read_text(isolate_content))

    return steps

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

  GTEST_TASK_PASSED = api.skylab.gen_task_result(
      'gtest',
      [],
  )

  def gen_tag_resp(api, tag, tasks):
    return {
        tag: api.skylab.gen_json_execution_response(tasks),
    }

  def simulate_ctp_response(api, tag, tasks):
    test_data = api.buildbucket.simulated_schedule_output(
        builds_service_pb2.BatchResponse(
            responses=[dict(schedule_build=build_pb2.Build(id=1234))]),
        step_name=(
            'test_pre_run.schedule tests on skylab.buildbucket.schedule'))
    test_data += api.buildbucket.simulated_collect_output(
        [
            api.skylab.test_with_multi_response(1234,
                                                gen_tag_resp(api, tag, tasks)),
        ],
        step_name='collect skylab results.buildbucket.collect')
    return test_data

  def _extract_skylab_req(steps):
    build_req = api.json.loads(
        steps['test_pre_run.schedule tests on skylab.buildbucket.schedule']
        .logs['request'])
    properties = build_req['requests'][0]['scheduleBuild'].get('properties', [])
    for req in properties['requests'].values():
      yield req

  def archive_gsuri_should_match_skylab_req(check, steps, target=TAST_TARGET):
    archive_step = ('prepare skylab tests.'
                    'upload skylab runtime deps for {target}.'
                    'Generic Archiving Steps.gsutil upload '
                    'lacros/lacros-amd64-generic-rel/571/{target}/'
                    'lacros_compressed.squash').format(target=target)
    archive_link = steps[archive_step].links['gsutil.upload']
    gs_uri = archive_link.replace('https://storage.cloud.google.com/', 'gs://')
    for req in _extract_skylab_req(steps):
      sw_deps = req['params']['softwareDependencies']
      dep_of_lacros = [
          '%s/lacros_compressed.squash' % d['lacrosGcsPath']
          for d in sw_deps
          if d.get('lacrosGcsPath')
      ]
      check(gs_uri in dep_of_lacros)

  def check_req_by_default_enabled_retry(check, steps):
    for req in _extract_skylab_req(steps):
      params_retry = req['params']['retry']
      check(params_retry['allow'] == True and params_retry['max'] == 3)

  def check_exe_rel_path_for_gtest(check, steps, rel_path):
    for req in _extract_skylab_req(steps):
      test = req['testPlan']['test'][0]
      check(rel_path in test['autotest']['testArgs'])

  yield api.test(
      'basic for tast',
      boilerplate(
          'chrome-test-builds', tast_expr='("group:mainline" && "dep:lacros")'),
      simulate_ctp_response(api, 'basic_EVE_TOT', [TASK_NO_CASE, TASK_PASSED]),
      api.post_process(post_process.StepCommandContains, 'compile', ['chrome']),
      api.post_process(archive_gsuri_should_match_skylab_req),
      api.post_process(post_process.StepSuccess, 'basic_EVE_TOT'),
      api.post_process(post_process.MustRun, 'basic_EVE_TOT.attempt: #1'),
      api.post_process(post_process.StepTextContains,
                       'basic_EVE_TOT.attempt: #2',
                       ['1 passed, 0 failed (1 total)']),
      api.post_process(check_req_by_default_enabled_retry),
      api.post_process(
          post_process.MustRun,
          ('prepare skylab tests.upload skylab runtime deps for %s.'
           'Generic Archiving Steps.'
           'Copy file out/Release/chrome') % TAST_TARGET,
      ),
      api.post_process(
          post_process.MustRun,
          ('prepare skylab tests.upload skylab runtime deps for %s.'
           'Generic Archiving Steps.'
           'Copy file metadata.json') % TAST_TARGET,
      ),
      api.post_process(post_process.DropExpectation),
  )

  inv_bundle = {
      'build-8839265267168653505':
          api.resultdb.Invocation(
              proto=invocation_pb2.Invocation(
                  state=invocation_pb2.Invocation.FINALIZED),),
  }
  yield api.test(
      'basic for gtest',
      boilerplate(
          'chrome-test-builds',
          test_args='--test-launcher-filter-file=../../testing/buildbot/filter',
          target_name=GTEST_TARGET),
      simulate_ctp_response(api, 'basic_EVE_TOT', [GTEST_TASK_PASSED]),
      api.resultdb.query(
          inv_bundle,
          step_name='basic_EVE_TOT results',
      ),
      api.override_step_data(
          'basic_EVE_TOT.gsutil Download test result for basic_EVE_TOT',
          api.test_utils.gtest_results(
              json.dumps({
                  'per_iteration_data': [{
                      'SpammyTest': [{
                          'elapsed_time_ms': 1000,
                          'output_snippet': 'line 1\nline 2',
                          'status': 'SUCCESS',
                      }],
                  }],
              }))),
      api.post_process(post_process.StepCommandContains, 'compile',
                       [GTEST_TARGET]),
      api.post_process(
          archive_gsuri_should_match_skylab_req, target=GTEST_TARGET),
      api.post_process(
          post_process.MustRun,
          'prepare skylab tests.'
          'upload skylab runtime deps for {target}.'
          'Generic Archiving Steps.'
          'Copy file out/Release/bin/run_{target}'.format(target=GTEST_TARGET),
      ),
      api.post_process(
          post_process.MustRun,
          ('prepare skylab tests.upload skylab runtime deps for %s.'
           'Generic Archiving Steps.'
           'Copy folder testing/buildbot/filters') % GTEST_TARGET,
      ),
      api.post_process(check_exe_rel_path_for_gtest,
                       'out/Release/bin/run_%s' % GTEST_TARGET),
      api.post_process(
          post_process.MustRun,
          'basic_EVE_TOT results',
      ),
      api.post_process(
          post_process.StepCommandContains,
          'basic_EVE_TOT results',
          ['build-8839265267168653505'],
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'gtest with invalid json result',
      boilerplate('chrome-test-builds', target_name=GTEST_TARGET),
      simulate_ctp_response(api, 'basic_EVE_TOT', [TASK_PASSED]),
      api.override_step_data(
          'basic_EVE_TOT.gsutil Download test result for basic_EVE_TOT',
          api.test_utils.gtest_results('not json')),
      api.post_process(post_process.StepFailure, 'basic_EVE_TOT'),
      api.post_process(post_process.StepTextContains, 'basic_EVE_TOT',
                       ['No valid result file returned.']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'CTP response with empty test case result',
      boilerplate(
          'chrome-test-builds', tast_expr='("group:mainline" && "dep:lacros")'),
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
      boilerplate('', tast_expr=TAST_TARGET, should_read_isolate=False),
      api.post_process(
          post_process.StepTextContains, 'basic_EVE_TOT',
          ['Test was not scheduled because of absent lacros_gcs_path.']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failed to find isolate file',
      boilerplate(
          'chrome-test-builds',
          tast_expr='("group:mainline" && "dep:lacros")',
          isolate_file_exists=False),
      api.post_process(
          post_process.StepFailure,
          'prepare skylab tests.collect runtime deps for %s' % TAST_TARGET),
      api.post_process(post_process.ResultReason,
                       'Failed to find the %s.isolate.' % TAST_TARGET),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failed to parse isolate file',
      boilerplate(
          'chrome-test-builds',
          tast_expr='("group:mainline" && "dep:lacros")',
          isolate_content=BAD_ISOLATE_TEXT),
      api.post_process(
          post_process.StepFailure,
          'prepare skylab tests.collect runtime deps for %s' % TAST_TARGET),
      api.post_process(post_process.ResultReason,
                       'Failed to parse the %s.isolate' % TAST_TARGET),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'target has no deps',
      boilerplate(
          'chrome-test-builds',
          tast_expr='("group:mainline" && "dep:lacros")',
          isolate_content=EMPTY_FILE_LIST),
      api.post_process(
          post_process.StepFailure,
          'prepare skylab tests.collect runtime deps for %s' % TAST_TARGET),
      api.post_process(post_process.ResultReason,
                       'No dependencies attached to target %s.' % TAST_TARGET),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'ci_only_test_on_ci_builder',
      boilerplate(
          'chrome-test-builds', tast_expr='("group:mainline" && "dep:lacros")'),
      simulate_ctp_response(api, 'basic_EVE_TOT', [TASK_PASSED]),
      api.post_process(post_process.StepTextContains, 'basic_EVE_TOT', [
          'This test will not be run on try builders',
          '1 passed, 0 failed (1 total)',
      ]),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'ci_only_test_on_trybot',
      boilerplate(
          'chrome-test-builds',
          tast_expr='dummy_tast',
          is_ci_build=False,
          should_read_isolate=False),
      api.post_process(post_process.StepTextContains, 'ci_only tests',
                       ['* basic_EVE_TOT']),
      api.post_process(
          post_process.DoesNotRun,
          'basic_EVE_TOT (with patch)',
      ),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'ci_only_test_on_trybot_bypass',
      boilerplate(
          'chrome-test-builds', tast_expr='dummy_tast', is_ci_build=False),
      api.step_data('parse description',
                    api.json.output({'Include-Ci-Only-Tests': ['true']})),
      api.post_process(
          post_process.MustRun,
          'basic_EVE_TOT (with patch)',
      ),
      api.post_process(post_process.StepTextContains,
                       'basic_EVE_TOT (with patch)',
                       [('This test is being run due to the'
                         ' Include-Ci-Only-Tests gerrit footer')]),
      api.post_process(post_process.DropExpectation),
  )
