# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from PB.recipe_modules.build.chromium_orchestrator.properties import (
    InputProperties)

from google.protobuf import timestamp_pb2

from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc
from RECIPE_MODULES.depot_tools.tryserver import api as tryserver
from RECIPE_MODULES.build.chromium_tests_builder_config import try_spec
from RECIPE_MODULES.build.chromium_orchestrator.api import (
    COMPILATOR_SWARMING_TASK_COLLECT_STEP)
from RECIPE_MODULES.build.chromium_orchestrator.api import (
    BUILD_CANCELED_SUMMARY)

from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import common as resultdb_common
from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import test_result as test_result_pb2
from PB.go.chromium.org.luci.analysis.proto.v1 import test_history

DEPS = [
    'chromium',
    'chromium_orchestrator',
    'chromium_swarming',
    'chromium_tests',
    'chromium_tests_builder_config',
    'code_coverage',
    'depot_tools/gclient',
    'depot_tools/gitiles',
    'depot_tools/tryserver',
    'filter',
    'flakiness',
    'profiles',
    'recipe_engine/buildbucket',
    'recipe_engine/cq',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/resultdb',
    'recipe_engine/runtime',
    'recipe_engine/step',
    'recipe_engine/swarming',
    'test_utils',
    'weetbix',
]


def RunSteps(api):
  assert api.tryserver.is_tryserver
  api.path.mock_add_paths(
      api.profiles.profile_dir().join('overall-merged.profdata'))

  return api.chromium_orchestrator.trybot_steps()


def GenTests(api):
  ctbc_api = api.chromium_tests_builder_config

  def ctbc_properties():
    return ctbc_api.properties(
        ctbc_api.properties_assembler_for_try_builder().with_mirrored_builder(
            builder_group='fake-group',
            builder='fake-builder',
        ).with_mirrored_tester(
            builder_group='fake-group',
            builder='fake-tester',
        ).assemble())

  def get_try_build(inverted_shard_experiment=False,
                    bail_early_experiment=False,
                    builder='fake-orchestrator'):
    experiments = []
    if inverted_shard_experiment:
      experiments.append('chromium_rts.inverted_rts')
    if bail_early_experiment:
      experiments.append('chromium_rts.inverted_rts_bail_early')
    return api.chromium.try_build(
        builder_group='fake-try-group',
        builder=builder,
        experiments=experiments,
        revision='d3advegg13',
        tags=api.buildbucket.tags(cq_equivalent_cl_group_key='12345'),
    )

  yield api.test(
      'basic',
      get_try_build(),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.code_coverage(use_clang_coverage=True),
      api.chromium_orchestrator.override_compilator_build_proto_fetch(),
      api.chromium_orchestrator.override_schedule_compilator_build(),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.post_process(
          post_process.StepCommandContains,
          'install infra/chromium/compilator_watcher.ensure_installed', [
              '-ensure-file', 'infra/chromium/compilator_watcher/${platform} '
              'git_revision:e841fc'
          ]),
      api.post_process(post_process.MustRun, 'set_output_gitiles_commit'),
      api.post_process(post_process.MustRun, 'trigger compilator (with patch)'),
      api.post_process(post_process.MustRun, 'browser_tests (with patch)'),
      api.post_process(post_process.MustRun,
                       'downloading cas digest all_test_binaries'),
      api.post_process(post_process.MustRun,
                       COMPILATOR_SWARMING_TASK_COLLECT_STEP),
      api.post_process(post_process.MustRun,
                       'run tools/clang/scripts/update.py'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.MustRun, 'download src-side deps'),
      api.post_process(post_process.MustRun,
                       'run tools/clang/scripts/update.py'),
      api.post_process(
          post_process.StepTextContains,
          'read test spec (fake-group.json)',
          ['[CLEANUP]/src/testing/buildbot/fake-group.json'],
      ),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'basic_branch',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.tryserver.gerrit_change_target_ref('refs/branch-heads/4472'),
      api.code_coverage(use_clang_coverage=True),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.post_process(post_process.MustRun, 'trigger compilator (with patch)'),
      api.post_process(post_process.MustRun, 'browser_tests (with patch)'),
      api.post_process(post_process.MustRun,
                       'downloading cas digest all_test_binaries'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'non_src_CL', ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium.try_build(
          builder='fake-orchestrator',
          git_repo='https://chromium.googlesource.com/v8/v8',
      ), api.code_coverage(use_clang_coverage=True),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ), api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.post_process(post_process.MustRun, 'trigger compilator (with patch)'),
      api.post_process(post_process.MustRun, 'browser_tests (with patch)'),
      api.post_process(post_process.MustRun,
                       'downloading cas digest all_test_binaries'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation))

  yield api.test(
      'without_patch_compilator',
      get_try_build(),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          with_patch=True, is_swarming_phase=False),
      api.chromium_orchestrator.override_compilator_steps(with_patch=False),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'retry shards with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'without patch', failures=['Test.One']),
      api.post_process(post_process.MustRun,
                       'trigger compilator (without patch)'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'coverage_not_enabled',
      get_try_build(),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          with_patch=True, is_swarming_phase=False),
      api.post_process(post_process.DoesNotRun,
                       'run tools/clang/scripts/update.py'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'clang_coverage_not_enabled',
      get_try_build(),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.code_coverage(use_java_coverage=True),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.chromium_orchestrator.override_compilator_build_proto_fetch(),
      api.chromium_orchestrator.override_schedule_compilator_build(),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.post_process(post_process.MustRun,
                       'downloading cas digest all_test_binaries'),
      api.post_process(post_process.DoesNotRun,
                       'run tools/clang/scripts/update.py'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no_builder_to_trigger_passed_in',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      api.post_process(post_process.DoesNotRun,
                       'trigger compilator (with patch)'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'depend_on_footer_failure',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.step_data(
          'parse description',
          api.json.output(
              {tryserver.constants.CQ_DEPEND_FOOTER: 'chromium:123456'})),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.ResultReasonRE,
                       r'Commit message footer Cq-Depend is not supported.*'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'missing_compilator_watcher_git_revision',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(compilator='fake-compilator',),
          }),
      api.code_coverage(use_clang_coverage=True),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.post_process(
          post_process.StepCommandContains,
          'install infra/chromium/compilator_watcher.ensure_installed', [
              '-ensure-file',
              'infra/chromium/compilator_watcher/${platform} latest'
          ]),
      api.post_process(post_process.MustRun, 'trigger compilator (with patch)'),
      api.post_process(post_process.MustRun, 'browser_tests (with patch)'),
      api.post_process(post_process.MustRun,
                       'downloading cas digest all_test_binaries'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'sub_build_canceled_status_and_in_global_shutdown',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.runtime.global_shutdown_on_step('compilator steps (with patch)'),
      api.chromium_orchestrator.override_schedule_compilator_build(),
      api.chromium_orchestrator.override_compilator_steps(
          sub_build_status=common_pb.CANCELED, empty_props=True),
      api.post_process(post_process.ResultReasonRE, BUILD_CANCELED_SUMMARY),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'dont_fetch_comp_build_if_canceled',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.runtime.global_shutdown_on_step('compilator steps (with patch)'),
      api.chromium_orchestrator.override_schedule_compilator_build(),
      api.chromium_orchestrator.override_compilator_steps(
          sub_build_status=common_pb.INFRA_FAILURE, empty_props=True),
      api.post_process(post_process.DoesNotRun, 'fetch compilator build proto'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'dont_collect_comp_task_if_not_ended',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.runtime.global_shutdown_on_step('download command lines'),
      api.chromium_orchestrator.override_schedule_compilator_build(),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.post_process(post_process.DoesNotRun,
                       COMPILATOR_SWARMING_TASK_COLLECT_STEP),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  fake_rts_command_lines = {
      'browser_tests': [
          './%s' % 'browser_tests', '--fake-without-patch-flag',
          '--fake-log-file', '$ISOLATED_OUTDIR/fake.log',
          '-filter=browser_tests.filter'
      ]
  }

  yield api.test(
      'quick run rts',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      api.chromium_tests_builder_config.try_build(
          builder_group='fake-group',
          builder='fake-tester',
          builder_db=ctbc.BuilderDatabase.create({
              'fake-group': {
                  'fake-tester':
                      ctbc.BuilderSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                      ),
              }
          }),
          try_db=ctbc.TryDatabase.create({
              'fake-group': {
                  'fake-tester':
                      ctbc.TrySpec.create(
                          mirrors=[
                              ctbc.TryMirror.create(
                                  builder_group='fake-group',
                                  buildername='fake-tester',
                                  tester='fake-tester',
                              ),
                          ],
                          regression_test_selection=try_spec.QUICK_RUN_ONLY,
                      ),
              }
          }),
      ),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.cq(run_mode='QUICK_DRY_RUN', top_level=True),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
          tests=['browser_tests', 'content_unittests']),
      api.chromium_orchestrator.override_compilator_steps(
          tests=['browser_tests', 'content_unittests']),
      api.step_data('read command lines (2)',
                    api.file.read_json(fake_rts_command_lines)),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.post_process(post_process.MustRun, 'RTS was used'),
      api.post_process(post_process.MustRun, 'quick run options'),
      api.post_process(
          post_process.LogContains,
          'trigger compilator (with patch)',
          'request',
          ['$recipe_engine/cq', 'QUICK_DRY_RUN'],
      ),
      api.post_process(post_process.PropertyEquals, 'rts_was_used', True),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'quick run enabled but not used',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      api.chromium_tests_builder_config.try_build(
          builder_group='fake-group',
          builder='fake-tester',
          builder_db=ctbc.BuilderDatabase.create({
              'fake-group': {
                  'fake-tester':
                      ctbc.BuilderSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                      ),
              }
          }),
          try_db=ctbc.TryDatabase.create({
              'fake-group': {
                  'fake-tester':
                      ctbc.TrySpec.create(
                          mirrors=[
                              ctbc.TryMirror.create(
                                  builder_group='fake-group',
                                  buildername='fake-tester',
                                  tester='fake-tester',
                              ),
                          ],
                          regression_test_selection=try_spec.QUICK_RUN_ONLY,
                      ),
              }
          }),
      ),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.cq(run_mode='QUICK_DRY_RUN', top_level=True),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
          tests=['browser_tests', 'content_unittests']),
      api.chromium_orchestrator.override_compilator_steps(
          tests=['browser_tests', 'content_unittests']),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.post_process(post_process.DoesNotRun, 'RTS was used'),
      api.post_process(post_process.MustRun, 'quick run options'),
      api.post_process(
          post_process.LogContains,
          'trigger compilator (with patch)',
          'request',
          ['$recipe_engine/cq', 'QUICK_DRY_RUN'],
      ),
      api.post_process(post_process.PropertiesDoNotContain, 'rts_was_used'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'non_swarmed_isolated_test',
      get_try_build(),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.code_coverage(use_clang_coverage=True),
      api.chromium_orchestrator.override_schedule_compilator_build(),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_tests.read_source_side_spec(
          'fake-group',
          {
              'fake-builder': {
                  'scripts': [{
                      "isolate_profile_data": True,
                      "name": "check_static_initializers",
                      "script": "check_static_initializers.py",
                      "swarming": {}
                  }],
              },
              'fake-tester': {
                  'gtest_tests': [{
                      'name': 'browser_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      },
                      'isolate_coverage_data': True,
                  },],
                  'isolated_scripts': [{
                      'isolate_name': 'angle_unittests',
                      'name': 'angle_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      }
                  }, {
                      'isolate_name': 'angle_unittests_no_swarm',
                      'name': 'angle_unittests_no_swarm',
                      'swarming': {
                          'can_use_on_swarming_builders': False,
                      },
                  }],
              },
          },
      ),
      api.post_process(post_process.StatusFailure),
      api.post_process(
          post_process.ResultReason,
          'angle_unittests_no_swarm is an isolated test but is not swarmed.',
      ),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no_tests_to_trigger',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_compilator_steps(empty_props=True),
      api.post_process(post_process.MustRun, 'trigger compilator (with patch)'),
      api.post_process(post_process.DoesNotRun, 'browser_tests (with patch)'),
      api.post_process(post_process.LogContains,
                       'trigger compilator (with patch)', 'request',
                       ['fake-try-group', 'fake-compilator']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_shards',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'with patch', failures=['Test.One']),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.post_process(post_process.DoesNotRun,
                       'trigger compilator (without patch)'),
      api.post_process(post_process.MustRun,
                       'browser_tests (retry shards with patch)'),
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  # without patch fails so failure is not due to CL
  yield api.test(
      'retry_shards_without_patch_fails_tryjob_succeeds',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
          tests=['browser_tests', 'content_unittests']),
      api.chromium_orchestrator.override_compilator_steps(
          tests=['browser_tests', 'content_unittests']),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.chromium_orchestrator.override_compilator_steps(with_patch=False),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'content_unittests', 'with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'retry shards with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'without patch', failures=['Test.One']),
      api.post_process(post_process.MustRun,
                       'trigger compilator (without patch)'),
      api.post_process(post_process.MustRun, 'browser_tests (without patch)'),
      api.post_process(post_process.DoesNotRun,
                       'content_unittests (without patch)'),
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  # without patch passes so failure is due to CL
  yield api.test(
      'retry_without_patch_passes_tryjob_fails',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
          tests=['browser_tests', 'content_unittests']),
      api.chromium_orchestrator.override_compilator_steps(
          tests=['browser_tests', 'content_unittests']),
      api.chromium_orchestrator.override_compilator_steps(
          with_patch=True, is_swarming_phase=False),
      api.chromium_orchestrator.override_compilator_steps(with_patch=False),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'content_unittests', 'with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'retry shards with patch', failures=['Test.One']),
      api.post_process(post_process.MustRun, 'browser_tests (without patch)'),
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_shards_invalid',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.override_step_data(
          'browser_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(test_results_json='', retcode=1),
              failure=True)),
      api.override_step_data(
          'browser_tests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True), failure=False)),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.post_process(post_process.MustRun,
                       'browser_tests (retry shards with patch)'),
      api.post_process(post_process.DoesNotRun,
                       'browser_tests (without patch)'),
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_shards_invalid_retry',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'retry shards with patch', failures=['Test.One']),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.chromium_orchestrator.override_compilator_steps(with_patch=False),
      api.post_process(post_process.MustRun,
                       'browser_tests (retry shards with patch)'),
      api.post_process(post_process.MustRun, 'browser_tests (without patch)'),
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_shards_all_invalid_results',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.override_step_data(
          'browser_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results('invalid', retcode=1),
              failure=True)),
      api.override_step_data(
          'browser_tests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results('invalid', retcode=1),
              failure=True)),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.post_process(post_process.MustRun,
                       'browser_tests (retry shards with patch)'),
      api.post_process(post_process.DoesNotRun,
                       'browser_tests (without patch)'),
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'skip_without_patch_local_tests_failed',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.chromium_orchestrator.override_compilator_steps(
          affected_files=['src/testing/buildbot/fake-group.json']),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False,
          sub_build_summary=("1 Test Suite(s) failed.\n\n"
                             "**headless_python_unittests** failed."),
          sub_build_status=common_pb.FAILURE,
      ),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'retry shards with patch', failures=['Test.One']),
      api.post_process(post_process.DoesNotRun,
                       'trigger compilator (without patch)'),
      api.post_process(post_process.MustRun,
                       'browser_tests (retry shards with patch)'),
      api.post_process(post_process.ResultReasonRE,
                       '.*headless_python_unittests.*'),
      api.post_process(post_process.ResultReasonRE, '.*browser_tests.*'),
      api.post_process(post_process.DoesNotRun,
                       'browser_tests (without patch)'),
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_without_patch_passes_local_tests_failed',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
          tests=['browser_tests', 'content_unittests']),
      api.chromium_orchestrator.override_compilator_steps(
          tests=['browser_tests', 'content_unittests']),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False,
          sub_build_summary=("1 Test Suite(s) failed.\n\n"
                             "**headless_python_unittests** failed."),
          sub_build_status=common_pb.FAILURE,
      ),
      api.chromium_orchestrator.override_compilator_steps(with_patch=False),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'content_unittests', 'with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'retry shards with patch', failures=['Test.One']),
      api.post_process(post_process.MustRun, 'browser_tests (without patch)'),
      api.post_process(post_process.DoesNotRun,
                       'content_unittests (without patch)'),
      api.post_process(post_process.ResultReasonRE,
                       '.*headless_python_unittests.*'),
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'compilator_skipping_coverage',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.code_coverage(use_clang_coverage=True),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.chromium_orchestrator.override_compilator_steps(
          skipping_coverage=True),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.post_process(post_process.MustRun, 'browser_tests (with patch)'),
      api.post_process(post_process.DoesNotRun,
                       'downloading cas digest all_test_binaries'),
      api.post_process(post_process.MustRun, 'download src-side deps'),
      api.post_process(
          # Only generates coverage data for the with patch step.
          post_process.DoesNotRun,
          'process clang code coverage data for overall test '
          'coverage.generate metadata for overall test coverage in 1 '
          'tests'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'code_coverage_trybot_with_patch',
      get_try_build(),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.code_coverage(use_clang_coverage=True),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.post_process(post_process.MustRun, 'browser_tests (with patch)'),
      api.post_process(post_process.MustRun,
                       'downloading cas digest all_test_binaries'),
      api.post_process(
          # Only generates coverage data for the with patch step.
          post_process.MustRun,
          'process clang code coverage data for overall test '
          'coverage.generate metadata for overall test coverage in 1 '
          'tests'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'code_coverage_trybot_retry_shards_with_patch',
      get_try_build(),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.code_coverage(use_clang_coverage=True),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.override_step_data(
          'browser_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'browser_tests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(True), failure=False)),
      api.post_process(post_process.MustRun, 'browser_tests (with patch)'),
      api.post_process(post_process.MustRun,
                       'downloading cas digest all_test_binaries'),
      api.post_process(
          # Only generates coverage data for the with patch step.
          post_process.MustRun,
          'process clang code coverage data for overall test '
          'coverage.generate metadata for overall test coverage in 2 '
          'tests'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'code_coverage_trybot_without_patch',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.code_coverage(use_clang_coverage=True),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(with_patch=False),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'retry shards with patch', failures=['Test.One']),
      api.post_process(post_process.MustRun,
                       'downloading cas digest all_test_binaries'),
      api.post_process(post_process.MustRun, 'browser_tests (without patch)'),
      api.post_process(
          # Generates coverage data for the with patch and retry shards with
          # patch steps. Without patch steps are always ignored.
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.generate '
          'metadata for overall test coverage in 2 tests'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_without_patch_fails_tests_and_local_tests',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
          tests=['browser_tests', 'content_unittests']),
      api.chromium_orchestrator.override_compilator_steps(
          tests=['browser_tests', 'content_unittests']),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False,
          sub_build_summary=("1 Test Suite(s) failed.\n\n"
                             "**headless_python_unittests** failed."),
          sub_build_status=common_pb.FAILURE,
      ),
      api.chromium_orchestrator.override_compilator_steps(with_patch=False),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'retry shards with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'without patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'content_unittests', 'with patch', failures=['Test.One']),
      api.post_process(post_process.ResultReasonRE,
                       '.*headless_python_unittests.*'),
      api.post_process(post_process.MustRun,
                       'trigger compilator (without patch)'),
      api.post_process(post_process.MustRun, 'browser_tests (without patch)'),
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'without_patch_compilator_missing_swarming_props',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          with_patch=True, is_swarming_phase=False),
      api.chromium_orchestrator.override_compilator_steps(
          with_patch=False, empty_props=True),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'retry shards with patch', failures=['Test.One']),
      api.post_process(post_process.MustRun,
                       'trigger compilator (without patch)'),
      api.post_process(post_process.DoesNotRun,
                       'browser_tests (without patch)'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failed_compilator_while_waiting_for_swarming_props',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_compilator_build_proto_fetch(
          status=common_pb.FAILURE),
      api.chromium_orchestrator.override_schedule_compilator_build(),
      api.chromium_orchestrator.override_compilator_steps(
          sub_build_status=common_pb.FAILURE,
          empty_props=True,
          sub_build_summary='Step compile (with patch) failed.'),
      api.post_process(post_process.ResultReason,
                       'Step compile (with patch) failed.'),
      api.post_process(post_process.MustRun,
                       COMPILATOR_SWARMING_TASK_COLLECT_STEP),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failed_wo_patch_compilator',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_schedule_compilator_build(
          step_name='trigger compilator (with patch)',
          build_id=12345,
      ),
      api.chromium_orchestrator.override_schedule_compilator_build(
          step_name='trigger compilator (without patch)',
          build_id=54321,
      ),
      api.chromium_orchestrator.override_compilator_build_proto_fetch(
          build_id=54321, status=common_pb.FAILURE),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.chromium_orchestrator.override_compilator_steps(
          with_patch=True, is_swarming_phase=False),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          with_patch=False,
          empty_props=True,
          sub_build_status=common_pb.FAILURE),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'retry shards with patch', failures=['Test.One']),
      api.post_process(post_process.MustRun,
                       'trigger compilator (without patch)'),
      api.post_process(post_process.MustRun,
                       COMPILATOR_SWARMING_TASK_COLLECT_STEP),
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'infra_failed_compilator_while_waiting_for_swarming_props',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_compilator_build_proto_fetch(
          status=common_pb.INFRA_FAILURE),
      api.chromium_orchestrator.override_schedule_compilator_build(),
      api.chromium_orchestrator.override_compilator_steps(
          sub_build_status=common_pb.INFRA_FAILURE,
          empty_props=True,
          sub_build_summary='Timeout waiting for compilator build'),
      api.post_process(post_process.ResultReason,
                       'Timeout waiting for compilator build'),
      api.post_process(post_process.MustRun,
                       COMPILATOR_SWARMING_TASK_COLLECT_STEP),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'canceled_compilator_while_waiting_for_swarming_props',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_compilator_steps(
          sub_build_status=common_pb.CANCELED,
          empty_props=True,
          sub_build_summary='Canceled'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failed_compilator_local_test',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.chromium_orchestrator.override_compilator_build_proto_fetch(
          status=common_pb.FAILURE),
      api.chromium_orchestrator.override_schedule_compilator_build(),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False,
          sub_build_status=common_pb.FAILURE,
          sub_build_summary=("1 Test Suite(s) failed.\n\n"
                             "**headless_python_unittests** failed.")),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'with patch', failures=['Test.One']),
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.MustRun,
                       COMPILATOR_SWARMING_TASK_COLLECT_STEP),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'compilator_canceled_at_local_test_phase',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          sub_build_status=common_pb.CANCELED,
          is_swarming_phase=False,
          sub_build_summary='Canceled'),
      api.chromium_orchestrator.override_compilator_steps(),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'sub_build_infra_failed',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_schedule_compilator_build(),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.chromium_orchestrator.override_compilator_steps(
          sub_build_status=common_pb.INFRA_FAILURE),
      api.post_process(post_process.MustRun, 'trigger compilator (with patch)'),
      api.post_process(post_process.DoesNotRun,
                       COMPILATOR_SWARMING_TASK_COLLECT_STEP),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  fake_command_lines = {
      'browser_tests': [
          './%s' % 'browser_tests', '--fake-without-patch-flag',
          '--fake-log-file', '$ISOLATED_OUTDIR/fake.log'
      ]
  }
  fake_inverted_rts_command_lines = {
      'browser_tests': [
          './%s' % 'browser_tests', '--fake-without-patch-flag',
          '--fake-log-file', '$ISOLATED_OUTDIR/fake.log',
          '-filter=inverted.filter'
      ]
  }

  yield api.test(
      'basic_with_inverted_shard_with_no_qr_bails_early',
      get_try_build(inverted_shard_experiment=True, bail_early_experiment=True),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.cq(run_mode='FULL_RUN'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  def _create_quick_run_build(include_coverage=True):
    reuseable_qr = build_pb2.Build(
        id=1234,
        status='SUCCESS',
        create_time=timestamp_pb2.Timestamp(seconds=1598338800),
        output=build_pb2.Build.Output())
    reuseable_qr.output.properties['rts_was_used'] = True
    if include_coverage:
      reuseable_qr.output.properties[
          'coverage_gs_bucket'] = "code-coverage-data"
      reuseable_qr.output.properties['merged_profdata_gs_paths'] = [
          "presubmit/chromium-review.googlesource.com/111111/1/try/fake-orchestrator/123456789/merged.profdata",
          "presubmit/chromium-review.googlesource.com/111111/1/try/fake-orchestrator_unit/123456789/merged.profdata"
      ]
    return reuseable_qr

  yield api.test(
      'basic_with_inverted_shard_with_qr_no_compilator_bails_early',
      get_try_build(
          inverted_shard_experiment=True,
          bail_early_experiment=True,
          builder='fake-orchestrator-inverse-fyi'),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.cq(run_mode='FULL_RUN', top_level=True),
      api.buildbucket.simulated_search_results(
          [_create_quick_run_build()], step_name='find successful Quick Runs'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'inverted_disabled_in_dry_run',
      get_try_build(inverted_shard_experiment=True),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.cq(run_mode='DRY_RUN'),
      api.post_process(post_process.DoesNotRun, 'find successful Quick Runs'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'inverted_shard_disabled_by_footer',
      get_try_build(inverted_shard_experiment=True),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.cq(run_mode='FULL_RUN'),
      api.step_data('parse description',
                    api.json.output({'Disable-Rts': ['true']})),
      api.post_process(post_process.DoesNotRun, 'find successful Quick Runs'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'inverted_bail_early_enabled_in_dry_run',
      get_try_build(inverted_shard_experiment=True, bail_early_experiment=True),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.cq(run_mode='DRY_RUN'),
      api.post_process(post_process.MustRun, 'find successful Quick Runs'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'basic_with_inverted_shard_with_qr_no_compilator_full_runs',
      get_try_build(inverted_shard_experiment=True, bail_early_experiment=True),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.cq(run_mode='FULL_RUN'),
      api.buildbucket.simulated_search_results(
          [_create_quick_run_build()], step_name='find successful Quick Runs'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'basic_with_inverted_shard_in_quick_run',
      get_try_build(inverted_shard_experiment=True, bail_early_experiment=True),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.cq(run_mode='QUICK_DRY_RUN'),
      api.post_process(post_process.DoesNotRun, 'find successful Quick Runs'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'inverted_rts_without_gitiles_commit_in_compilator',
      get_try_build(inverted_shard_experiment=True, bail_early_experiment=True),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.cq(run_mode='FULL_RUN'),
      api.code_coverage(use_clang_coverage=True),
      api.m.buildbucket.simulated_search_results(
          [_create_quick_run_build()], step_name='find successful Quick Runs'),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
          tests=['browser_tests', 'content_unittests']),
      api.chromium_orchestrator.override_reused_compilator_steps(
          tests=['browser_tests', 'content_unittests'],
          empty_gitiles_commit=True),
      api.post_process(post_process.MustRun,
                       'compilator gitiles_commit missing'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'with_inverted_shard_with_successful_qr_none_invertable',
      get_try_build(inverted_shard_experiment=True, bail_early_experiment=True),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.cq(run_mode='FULL_RUN'),
      api.code_coverage(use_clang_coverage=True),
      api.m.buildbucket.simulated_search_results(
          [_create_quick_run_build()], step_name='find successful Quick Runs'),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
          tests=['browser_tests', 'content_unittests']),
      api.chromium_orchestrator.override_reused_compilator_steps(
          tests=['browser_tests', 'content_unittests']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'with_inverted_shard_with_successful_qr',
      get_try_build(inverted_shard_experiment=True, bail_early_experiment=True),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.cq(run_mode='FULL_RUN'),
      api.code_coverage(use_clang_coverage=True),
      api.m.buildbucket.simulated_search_results(
          [_create_quick_run_build()], step_name='find successful Quick Runs'),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
          tests=['browser_tests', 'content_unittests']),
      api.chromium_orchestrator.override_reused_compilator_steps(
          tests=['browser_tests', 'content_unittests']),
      api.step_data('read command lines (2)',
                    api.file.read_json(fake_inverted_rts_command_lines)),
      api.post_process(post_process.MustRun, 'browser_tests (with patch)'),
      api.post_process(
          api.swarming.check_triggered_request,
          'test_pre_run (with patch).[trigger] '
          'browser_tests (with patch)', lambda check, req: check(
              is_subsequence(req[0].command, fake_inverted_rts_command_lines[
                  'browser_tests']))),
      api.post_process(post_process.MustRun,
                       'downloading cas digest all_test_binaries'),
      api.post_process(
          post_process.StepCommandContains,
          'gsutil download Quick Run overall coverage from GS', [
              'gs://code-coverage-data/presubmit/chromium-review.googlesource.com/111111/1/try/fake-orchestrator/123456789/merged.profdata'
          ]),
      api.post_process(
          post_process.StepCommandContains,
          'gsutil download Quick Run unit coverage from GS', [
              'gs://code-coverage-data/presubmit/chromium-review.googlesource.com/111111/1/try/fake-orchestrator_unit/123456789/merged.profdata'
          ]),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'with_inverted_shard_with_successful_qr_no_prev_artifacts',
      get_try_build(inverted_shard_experiment=True, bail_early_experiment=True),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.cq(run_mode='FULL_RUN'),
      api.code_coverage(use_clang_coverage=True),
      api.m.buildbucket.simulated_search_results(
          [_create_quick_run_build(False)],
          step_name='find successful Quick Runs'),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
          tests=['browser_tests', 'content_unittests']),
      api.chromium_orchestrator.override_reused_compilator_steps(
          tests=['browser_tests', 'content_unittests']),
      api.step_data('read command lines (2)',
                    api.file.read_json(fake_inverted_rts_command_lines)),
      api.post_process(post_process.MustRun, 'browser_tests (with patch)'),
      api.post_process(
          api.swarming.check_triggered_request,
          'test_pre_run (with patch).[trigger] '
          'browser_tests (with patch)', lambda check, req: check(
              is_subsequence(req[0].command, fake_inverted_rts_command_lines[
                  'browser_tests']))),
      api.post_process(post_process.MustRun,
                       'downloading cas digest all_test_binaries'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  def is_subsequence(containing, contained):
    containing_str = ' '.join(containing)
    contained_str = ' '.join(contained)
    return contained_str in containing_str

  yield api.test(
      'without_patch_tests_contain_command_lines_from_without_patch_compilator',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-orchestrator',
      ),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
          tests=['browser_tests', 'content_unittests']),
      api.chromium_orchestrator.override_compilator_steps(
          tests=['browser_tests', 'content_unittests']),
      api.chromium_orchestrator.override_compilator_steps(
          with_patch=True, is_swarming_phase=False),
      api.chromium_orchestrator.override_compilator_steps(with_patch=False),
      api.step_data('read command lines',
                    api.file.read_json(fake_command_lines)),
      api.step_data('read command lines (2)',
                    api.file.read_json(fake_inverted_rts_command_lines)),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'content_unittests', 'with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'retry shards with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'browser_tests', 'without patch', failures=['Test.One']),
      api.post_process(post_process.MustRun,
                       'trigger compilator (without patch)'),
      api.post_process(post_process.MustRun, 'browser_tests (without patch)'),
      api.post_process(
          api.swarming.check_triggered_request,
          'test_pre_run (without patch).[trigger] '
          'browser_tests (without patch)', lambda check, req: check(
              is_subsequence(req[0].command, fake_command_lines['browser_tests']
                            ))),
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  def _generate_test_result(test_id,
                            test_variant,
                            status=test_result_pb2.PASS,
                            tags=None):
    vh = 'variant_hash'
    tr = test_result_pb2.TestResult(
        test_id=test_id,
        variant=test_variant,
        variant_hash=vh,
        expected=False,
        status=status,
    )
    if tags:
      all_tags = getattr(tr, 'tags')
      all_tags.append(tags)
    return tr

  correct_variant = resultdb_common.Variant()
  variant_def = getattr(correct_variant, 'def')
  variant_def['os'] = 'Ubuntu-18'
  variant_def['test_suite'] = ('browser_tests')

  tags = resultdb_common.StringPair(key='test_name', value='Test:Test1')

  test_id = 'ninja://browser_tests/Test:Test1'
  inv = 'invocations/build:8945511751514863184'
  current_patchset_invocations = {
      inv:
          api.resultdb.Invocation(test_results=[
              _generate_test_result(test_id, correct_variant, tags=tags)
          ])
  }
  recent_run = test_history.QueryTestHistoryResponse(
      verdicts=[], next_page_token='dummy_token')

  yield api.test(
      'new_flaky_test',
      get_try_build(),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_compilator_build_proto_fetch(),
      api.chromium_orchestrator.override_schedule_compilator_build(),
      api.chromium_orchestrator.override_compilator_steps(
          affected_files=['src/chrome/test.cc', 'src/components/file2.cc']),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
      ),
      api.resultdb.query(
          current_patchset_invocations,
          ('collect tasks (with patch).browser_tests results'),
      ),
      api.flakiness(check_for_flakiness=True),
      api.weetbix.query_test_history(
          recent_run,
          'ninja://browser_tests/Test:Test1',
          parent_step_name='searching_for_new_tests',
      ),
      api.override_step_data(('test new tests for flakiness.'
                              'collect tasks (check flakiness shard #0).'
                              'browser_tests results'),
                             stdout=api.json.invalid(
                                 api.test_utils.rdb_results(
                                     'browser_tests',
                                     flaky_failing_tests=['Test.One'],
                                 ))),
      api.post_process(post_process.MustRun, 'calculate flake rates'),
      api.post_process(post_process.ResultReasonRE, '.*browser_tests.*'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'flaky_swarming_and_local_test_failure',
      get_try_build(),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_compilator_build_proto_fetch(),
      api.chromium_orchestrator.override_schedule_compilator_build(),
      api.chromium_orchestrator.override_compilator_build_proto_fetch(),
      api.chromium_orchestrator.override_schedule_compilator_build(),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
          tests=['browser_tests', 'content_unittests'],
      ),
      api.chromium_orchestrator.override_compilator_steps(
          tests=['browser_tests', 'content_unittests'],
          affected_files=['src/chrome/test.cc', 'src/components/file2.cc']),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False,
          sub_build_status=common_pb.FAILURE,
          sub_build_summary=("1 Test Suite(s) failed.\n\n"
                             "**headless_python_unittests** failed.")),
      api.resultdb.query(
          current_patchset_invocations,
          ('collect tasks (with patch).browser_tests results'),
      ),
      api.flakiness(check_for_flakiness=True),
      api.weetbix.query_test_history(
          recent_run,
          'ninja://browser_tests/Test:Test1',
          parent_step_name='searching_for_new_tests',
      ),
      api.override_step_data(('test new tests for flakiness.'
                              'collect tasks (check flakiness shard #0).'
                              'browser_tests results'),
                             stdout=api.json.invalid(
                                 api.test_utils.rdb_results(
                                     'browser_tests',
                                     flaky_failing_tests=['Test.One'],
                                 ))),
      api.post_process(post_process.MustRun, 'calculate flake rates'),
      api.post_process(post_process.ResultReasonRE, '.*browser_tests.*'),
      api.post_process(post_process.ResultReasonRE,
                       '.*headless_python_unittests.*'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no_flaky_tests',
      get_try_build(),
      ctbc_properties(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='fake-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_compilator_build_proto_fetch(),
      api.chromium_orchestrator.override_schedule_compilator_build(),
      api.chromium_orchestrator.override_schedule_compilator_build(),
      api.chromium_orchestrator.override_test_spec(
          builder_group='fake-group',
          builder='fake-builder',
          tester='fake-tester',
          tests=['browser_tests', 'content_unittests'],
      ),
      api.chromium_orchestrator.override_compilator_steps(
          tests=['browser_tests', 'content_unittests'],
          affected_files=['src/chrome/test.cc', 'src/components/file2.cc']),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.resultdb.query(
          current_patchset_invocations,
          ('collect tasks (with patch).browser_tests results'),
      ),
      api.flakiness(check_for_flakiness=True),
      api.weetbix.query_test_history(
          recent_run,
          'ninja://browser_tests/Test:Test1',
          parent_step_name='searching_for_new_tests',
      ),
      api.resultdb.query(
          current_patchset_invocations,
          ('test new tests for flakiness.'
           'collect tasks (check flakiness shard #0).browser_tests results'),
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
