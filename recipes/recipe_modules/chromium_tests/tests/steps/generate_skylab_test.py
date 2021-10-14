# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import itertools
import json

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

from recipe_engine import post_process

PYTHON_VERSION_COMPATIBILITY = "PY2"

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
    'recipe_engine/raw_io',
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
                  build_id=8945511751514863184,
                  builder_group='chromium.chromiumos',
                  builder='lacros-amd64-generic-rel',
                  tast_expr='',
                  test_args='',
                  isolate_content=GOOD_ISOLATE_TEXT,
                  isolate_file_exists=True,
                  is_ci_build=True,
                  target_name=TAST_TARGET,
                  should_read_isolate=True):
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
          build_id=build_id,
          builder_group=builder_group,
          builder=builder,
          parent_buildername='Linux Builder',
          builder_db=builder_db,
      )
    else:
      build_gen = api.chromium_tests_builder_config.try_build(
          build_id=build_id,
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

  def _extract_skylab_req(steps):
    return api.skylab.step_logs_to_ctp_by_tag(
        steps['test_pre_run.schedule skylab tests.buildbucket.schedule'].logs)

  def archive_gsuri_should_match_skylab_req(check,
                                            steps,
                                            build_id=8945511751514863184,
                                            target=TAST_TARGET):
    archive_step = ('prepare skylab tests.'
                    'upload skylab runtime deps for {target}.'
                    'Generic Archiving Steps.gsutil upload '
                    'lacros/{build_id}/{target}/'
                    'lacros_compressed.squash').format(
                        build_id=build_id, target=target)
    archive_link = steps[archive_step].links['gsutil.upload']
    gs_uri = archive_link.replace('https://storage.cloud.google.com/', 'gs://')
    for req in _extract_skylab_req(steps).values():
      sw_deps = req['params']['softwareDependencies']
      dep_of_lacros = [
          d['lacrosGcsPath'] for d in sw_deps if d.get('lacrosGcsPath')
      ]
      check(gs_uri == '%s/lacros_compressed.squash' % dep_of_lacros[0])

  def check_req_by_default_enabled_retry(check, steps):
    for req in _extract_skylab_req(steps).values():
      params_retry = req['params']['retry']
      check(params_retry['allow'] == True and params_retry['max'] == 3)

  def check_exe_rel_path_for_gtest(check, steps, rel_path):
    for req in _extract_skylab_req(steps).values():
      test = req['testPlan']['test'][0]
      check(rel_path in test['autotest']['testArgs'])

  def check_qs_account(check, steps, expected_qs):
    for req in _extract_skylab_req(steps).values():
      check(req['params']['scheduling']['qsAccount'] == expected_qs)

  yield api.test(
      'basic for tast',
      boilerplate(
          'chrome-test-builds', tast_expr='("group:mainline" && "dep:lacros")'),
      api.skylab.gen_schedule_build_resps('test_pre_run.schedule skylab tests',
                                          1),
      api.skylab.wait_on_suites(
          'find test runner build',
          1,
          runner_builds=[(901, common_pb2.FAILURE),
                         (902, common_pb2.INFRA_FAILURE),
                         (903, common_pb2.SUCCESS)]),
      api.post_process(post_process.StepCommandContains, 'compile', ['chrome']),
      api.post_process(archive_gsuri_should_match_skylab_req),
      api.post_process(check_req_by_default_enabled_retry),
      api.post_process(check_qs_account, 'lacros'),
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
      api.override_step_data(
          'basic_EVE_TOT results',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  failing_suites=['basic_EVE_TOT'],
                  skipped_suites=['basic_EVE_TOT']))),
      api.post_process(post_process.StepFailure, 'basic_EVE_TOT.attempt: #1'),
      api.post_process(post_process.StepException, 'basic_EVE_TOT.attempt: #2'),
      api.post_process(post_process.StepSuccess, 'basic_EVE_TOT.attempt: #3'),
      api.post_process(post_process.StepFailure, 'basic_EVE_TOT'),
      api.post_process(
          post_process.ResultReason,
          '1 Test Suite(s) failed.\n\n**basic_EVE_TOT** '
          'failed because of:\n\n- basic_EVE_TOT_test_case1'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'basic for gtest',
      boilerplate(
          'chrome-test-builds',
          test_args='--test-launcher-filter-file=../../testing/buildbot/filter',
          target_name=GTEST_TARGET),
      api.skylab.gen_schedule_build_resps('test_pre_run.schedule skylab tests',
                                          1),
      api.skylab.wait_on_suites(
          'find test runner build',
          1,
          runner_builds=[(902, common_pb2.SUCCESS)]),
      api.override_step_data(
          'basic_EVE_TOT results',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  failing_suites=['basic_EVE_TOT'],
                  skipped_suites=['basic_EVE_TOT']))),
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
      api.post_process(post_process.StepCommandContains, 'compile',
                       [GTEST_TARGET]),
      api.post_process(
          archive_gsuri_should_match_skylab_req, target=GTEST_TARGET),
      api.post_process(check_exe_rel_path_for_gtest,
                       'out/Release/bin/run_%s' % GTEST_TARGET),
      api.post_process(post_process.StepFailure, 'basic_EVE_TOT'),
      api.post_process(
          post_process.ResultReason,
          '1 Test Suite(s) failed.\n\n**basic_EVE_TOT** '
          'failed because of:\n\n- basic_EVE_TOT_test_case1'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'test from fyi builder',
      boilerplate('chrome-test-builds', builder='lacros-amd64-generic-fyi'),
      api.skylab.gen_schedule_build_resps('test_pre_run.schedule skylab tests',
                                          1),
      api.post_process(check_qs_account, 'lacros_fyi'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'RDB returned empty test_results',
      boilerplate(
          'chrome-test-builds', tast_expr='("group:mainline" && "dep:lacros")'),
      api.skylab.gen_schedule_build_resps('test_pre_run.schedule skylab tests',
                                          1),
      api.skylab.wait_on_suites('find test runner build', 1),
      api.override_step_data(
          'basic_EVE_TOT results',
          stdout=api.raw_io.output_text(api.test_utils.rdb_results())),
      api.post_process(post_process.StepCommandContains, 'compile', ['chrome']),
      api.post_process(archive_gsuri_should_match_skylab_req),
      api.post_process(post_process.StepException, 'basic_EVE_TOT'),
      api.post_process(post_process.StepTextContains, 'basic_EVE_TOT',
                       ['Test did not run or failed to report to ResultDB.']),
      api.post_process(post_process.DropExpectation),
  )

  # CrOS lab has outage and no response from the buildbucket call.
  yield api.test(
      'Skylab outage',
      boilerplate(
          'chrome-test-builds', tast_expr='("group:mainline" && "dep:lacros")'),
      api.skylab.gen_schedule_build_resps('test_pre_run.schedule skylab tests',
                                          1),
      api.post_process(post_process.StepException, 'basic_EVE_TOT'),
      api.post_process(post_process.ResultReason,
                       '1 Test Suite(s) failed.\n\n**basic_EVE_TOT** failed.'),
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
      api.skylab.gen_schedule_build_resps('test_pre_run.schedule skylab tests',
                                          1),
      api.skylab.wait_on_suites('find test runner build', 1),
      api.post_process(post_process.StepTextContains, 'basic_EVE_TOT', [
          'This test will not be run on try builders',
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
