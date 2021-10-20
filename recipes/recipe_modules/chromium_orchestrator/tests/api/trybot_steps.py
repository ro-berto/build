# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from PB.recipe_modules.build.chromium_orchestrator.properties import (
    InputProperties)

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc
from RECIPE_MODULES.depot_tools.tryserver import api as tryserver
from RECIPE_MODULES.build.chromium_tests_builder_config import try_spec

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

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
    'profiles',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'recipe_engine/swarming',
    'test_utils',
]


def RunSteps(api):
  assert api.tryserver.is_tryserver
  api.path.mock_add_paths(
      api.profiles.profile_dir().join('overall-merged.profdata'))

  return api.chromium_orchestrator.trybot_steps()


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.code_coverage(use_clang_coverage=True),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.chromium_orchestrator.fake_head_revision(),
      api.post_process(post_process.StepCommandContains, 'bot_update',
                       ['--refs', 'refs/heads/main']),
      api.post_process(post_process.StepCommandContains, 'bot_update',
                       ['--patch_ref']),
      api.chromium_orchestrator.override_test_spec(),
      api.post_process(
          post_process.StepCommandContains,
          'install infra/chromium/compilator_watcher.ensure_installed', [
              '-ensure-file', 'infra/chromium/compilator_watcher/${platform} '
              'git_revision:e841fc'
          ]),
      api.post_process(post_process.MustRun, 'trigger compilator (with patch)'),
      api.post_process(post_process.MustRun, 'browser_tests (with patch)'),
      api.post_process(post_process.MustRun,
                       'downloading cas digest all_test_binaries'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'basic_branch',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.tryserver.gerrit_change_target_ref('refs/branch-heads/4472'),
      api.code_coverage(use_clang_coverage=True),
      api.chromium_orchestrator.fake_head_revision('refs/branch-heads/4472'),
      api.chromium_orchestrator.override_test_spec(),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.post_process(post_process.StepCommandContains, 'bot_update',
                       ['--refs', 'refs/branch-heads/4472']),
      api.post_process(post_process.MustRun, 'trigger compilator (with patch)'),
      api.post_process(post_process.MustRun, 'browser_tests (with patch)'),
      api.post_process(post_process.MustRun,
                       'downloading cas digest all_test_binaries'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'non_src_CL',
      api.chromium.try_build(
          builder='linux-rel-orchestrator',
          git_repo='https://chromium.googlesource.com/v8/v8'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.code_coverage(use_clang_coverage=True),
      api.chromium_orchestrator.fake_head_revision(),
      api.override_step_data(
          'read v8/v8 HEAD revision at refs/heads/main',
          api.m.json.output({'log': [{
              'commit': 'v8deadbeef'
          }]})),
      api.chromium_orchestrator.override_test_spec(),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.post_process(post_process.StepCommandContains, 'bot_update',
                       ['--revision', 'src@{}'.format('deadbeef')]),
      api.post_process(post_process.StepCommandContains, 'bot_update',
                       ['--revision', 'src/v8@{}'.format('v8deadbeef')]),
      api.post_process(post_process.MustRun, 'trigger compilator (with patch)'),
      api.post_process(post_process.MustRun, 'browser_tests (with patch)'),
      api.post_process(post_process.MustRun,
                       'downloading cas digest all_test_binaries'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no_builder_to_trigger_passed_in',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.post_process(post_process.DoesNotRun,
                       'trigger compilator (with patch)'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'depend_on_footer_failure',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
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
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(compilator='linux-rel-compilator',),
          }),
      api.code_coverage(use_clang_coverage=True),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.chromium_orchestrator.fake_head_revision(),
      api.chromium_orchestrator.override_test_spec(),
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
      'quick run rts',
      api.properties(
          **{
              "$recipe_engine/cq": {
                  "active": True,
                  "dryRun": True,
                  "runMode": "QUICK_DRY_RUN",
                  "topLevel": True
              }
          }),
      api.chromium_tests_builder_config.try_build(
          builder_group='tryserver.chromium.test',
          builder='rts-rel',
          builder_db=ctbc.BuilderDatabase.create({
              'chromium.test': {
                  'chromium-rel':
                      ctbc.BuilderSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                      ),
              }
          }),
          try_db=ctbc.TryDatabase.create({
              'tryserver.chromium.test': {
                  'rts-rel':
                      ctbc.TrySpec.create(
                          mirrors=[
                              ctbc.TryMirror.create(
                                  builder_group='chromium.test',
                                  buildername='chromium-rel',
                                  tester='chromium-rel',
                              ),
                          ],
                          regression_test_selection=try_spec.QUICK_RUN_ONLY,
                      ),
              }
          }),
      ),
      api.chromium_orchestrator.fake_head_revision(),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_tests.read_source_side_spec('chromium.test', {
          'chromium-rel': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.post_process(post_process.MustRun, 'quick run options'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no_tests_to_trigger',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.fake_head_revision(),
      api.chromium_orchestrator.override_test_spec(),
      api.chromium_orchestrator.override_compilator_steps(empty_props=True),
      api.post_process(post_process.MustRun, 'trigger compilator (with patch)'),
      api.post_process(post_process.DoesNotRun, 'browser_tests (with patch)'),
      api.post_process(post_process.LogContains,
                       'trigger compilator (with patch)', 'request',
                       ['tryserver.chromium.linux', 'linux-rel-compilator']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_shards',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.fake_head_revision(),
      api.chromium_orchestrator.override_test_spec(),
      api.override_step_data(
          'browser_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'browser_tests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(True), failure=False)),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.post_process(post_process.DoesNotRun,
                       'trigger compilator (without patch)'),
      api.post_process(post_process.MustRun,
                       'browser_tests (retry shards with patch)'),
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.MustRun, 'FindIt Flakiness'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  # without patch fails so failure is not due to CL
  yield api.test(
      'retry_shards_without_patch_fails_tryjob_succeeds',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.fake_head_revision(),
      api.chromium_orchestrator.override_test_spec(
          tests=['browser_tests', 'content_unittests']),
      api.chromium_orchestrator.override_compilator_steps(
          tests=['browser_tests', 'content_unittests']),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.chromium_orchestrator.override_compilator_steps(with_patch=False),
      api.override_step_data(
          'browser_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'content_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'browser_tests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'content_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(True), failure=False)),
      api.override_step_data(
          'browser_tests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.post_process(post_process.MustRun,
                       'trigger compilator (without patch)'),
      api.post_process(post_process.MustRun, 'browser_tests (without patch)'),
      api.post_process(post_process.DoesNotRun,
                       'content_unittests (without patch)'),
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.MustRun, 'FindIt Flakiness'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  # without patch passes so failure is due to CL
  yield api.test(
      'retry_without_patch_passes_tryjob_fails',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.fake_head_revision(),
      api.chromium_orchestrator.override_test_spec(
          tests=['browser_tests', 'content_unittests']),
      api.chromium_orchestrator.override_compilator_steps(
          tests=['browser_tests', 'content_unittests']),
      api.chromium_orchestrator.override_compilator_steps(
          with_patch=True, is_swarming_phase=False),
      api.chromium_orchestrator.override_compilator_steps(with_patch=False),
      api.override_step_data(
          'content_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'content_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(True), failure=False)),
      api.override_step_data(
          'browser_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'browser_tests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'browser_tests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(True), failure=False)),
      api.post_process(post_process.MustRun, 'browser_tests (without patch)'),
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.MustRun, 'FindIt Flakiness'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_shards_invalid',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.fake_head_revision(),
      api.chromium_orchestrator.override_test_spec(),
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
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.fake_head_revision(),
      api.chromium_orchestrator.override_test_spec(),
      api.override_step_data(
          'browser_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=False), failure=True)),
      api.override_step_data(
          'browser_tests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(test_results_json='', retcode=1),
              failure=True)),
      api.override_step_data(
          'browser_tests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(passing=True), failure=False)),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.chromium_orchestrator.override_compilator_steps(with_patch=False),
      api.post_process(post_process.MustRun,
                       'browser_tests (retry shards with patch)'),
      api.post_process(post_process.MustRun, 'browser_tests (without patch)'),
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.MustRun, 'FindIt Flakiness'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_shards_all_invalid_results',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.fake_head_revision(),
      api.chromium_orchestrator.override_test_spec(),
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
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.fake_head_revision(),
      api.chromium_orchestrator.override_test_spec(),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False,
          sub_build_summary=("1 Test Suite(s) failed.\n\n"
                             "**headless_python_unittests** failed."),
          sub_build_status=common_pb.FAILURE,
      ),
      api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('testing/buildbot/chromium.linux.json')),
      api.override_step_data(
          'browser_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'browser_tests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
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
      api.post_process(post_process.MustRun, 'FindIt Flakiness'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_without_patch_passes_local_tests_failed',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.fake_head_revision(),
      api.chromium_orchestrator.override_test_spec(
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
      api.override_step_data(
          'browser_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'content_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'browser_tests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'content_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(True), failure=False)),
      api.override_step_data(
          'browser_tests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(True), failure=False)),
      api.post_process(post_process.MustRun, 'browser_tests (without patch)'),
      api.post_process(post_process.DoesNotRun,
                       'content_unittests (without patch)'),
      api.post_process(post_process.ResultReasonRE,
                       '.*headless_python_unittests.*'),
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.MustRun, 'FindIt Flakiness'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'code_coverage_trybot_with_patch',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.code_coverage(use_clang_coverage=True),
      api.chromium_orchestrator.fake_head_revision(),
      api.chromium_orchestrator.override_test_spec(),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.post_process(post_process.MustRun, 'browser_tests (with patch)'),
      api.post_process(post_process.MustRun,
                       'downloading cas digest all_test_binaries'),
      api.post_process(
          # Only generates coverage data for the with patch step.
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.generate '
          'metadata for overall test coverage in 1 tests'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'code_coverage_trybot_retry_shards_with_patch',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.code_coverage(use_clang_coverage=True),
      api.chromium_orchestrator.fake_head_revision(),
      api.chromium_orchestrator.override_test_spec(),
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
          'process clang code coverage data for overall test coverage.generate '
          'metadata for overall test coverage in 2 tests'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'code_coverage_trybot_without_patch',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.code_coverage(use_clang_coverage=True),
      api.chromium_orchestrator.fake_head_revision(),
      api.chromium_orchestrator.override_test_spec(),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(with_patch=False),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False),
      api.override_step_data(
          'browser_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'browser_tests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
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
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.fake_head_revision(),
      api.chromium_orchestrator.override_test_spec(
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
      api.override_step_data(
          'browser_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'browser_tests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'browser_tests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'content_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'content_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(True), failure=False)),
      api.post_process(post_process.ResultReasonRE,
                       '.*headless_python_unittests.*'),
      api.post_process(post_process.MustRun,
                       'trigger compilator (without patch)'),
      api.post_process(post_process.MustRun, 'browser_tests (without patch)'),
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.MustRun, 'FindIt Flakiness'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'without_patch_compilator_missing_swarming_props',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.fake_head_revision(),
      api.chromium_orchestrator.override_test_spec(),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          with_patch=True, is_swarming_phase=False),
      api.chromium_orchestrator.override_compilator_steps(
          with_patch=False, empty_props=True),
      api.override_step_data(
          'browser_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'browser_tests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.post_process(post_process.MustRun,
                       'trigger compilator (without patch)'),
      api.post_process(post_process.DoesNotRun,
                       'browser_tests (without patch)'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failed_compilator_while_waiting_for_swarming_props',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_test_spec(),
      api.chromium_orchestrator.fake_head_revision(),
      api.chromium_orchestrator.override_compilator_steps(
          sub_build_status=common_pb.FAILURE,
          empty_props=True,
          sub_build_summary='Step compile (with patch) failed.'),
      api.post_process(post_process.ResultReason,
                       'Step compile (with patch) failed.'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failed_wo_patch_compilator',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.fake_head_revision(),
      api.chromium_orchestrator.override_test_spec(),
      api.chromium_orchestrator.override_compilator_steps(
          with_patch=True, is_swarming_phase=False),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          with_patch=False,
          empty_props=True,
          sub_build_status=common_pb.FAILURE),
      api.override_step_data(
          'browser_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'browser_tests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.post_process(post_process.MustRun,
                       'trigger compilator (without patch)'),
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.MustRun, 'FindIt Flakiness'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'infra_failed_compilator_while_waiting_for_swarming_props',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_test_spec(),
      api.chromium_orchestrator.fake_head_revision(),
      api.chromium_orchestrator.override_compilator_steps(
          sub_build_status=common_pb.INFRA_FAILURE,
          empty_props=True,
          sub_build_summary='Timeout waiting for compilator build'),
      api.post_process(post_process.ResultReason,
                       'Timeout waiting for compilator build'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'canceled_compilator_while_waiting_for_swarming_props',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_test_spec(),
      api.chromium_orchestrator.fake_head_revision(),
      api.chromium_orchestrator.override_compilator_steps(
          sub_build_status=common_pb.CANCELED,
          empty_props=True,
          sub_build_summary='Canceled'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failed_compilator_local_test',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.fake_head_revision(),
      api.chromium_orchestrator.override_test_spec(),
      api.chromium_orchestrator.override_compilator_steps(),
      api.chromium_orchestrator.override_compilator_steps(
          is_swarming_phase=False,
          sub_build_status=common_pb.FAILURE,
          sub_build_summary=("1 Test Suite(s) failed.\n\n"
                             "**headless_python_unittests** failed.")),
      api.override_step_data(
          'browser_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'browser_tests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(True), failure=False)),
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.MustRun, 'FindIt Flakiness'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'compilator_canceled_at_local_test_phase',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.fake_head_revision(),
      api.chromium_orchestrator.override_test_spec(),
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
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.override_test_spec(),
      api.chromium_orchestrator.fake_head_revision(),
      api.chromium_orchestrator.override_compilator_steps(
          sub_build_status=common_pb.INFRA_FAILURE),
      api.post_process(post_process.MustRun, 'trigger compilator (with patch)'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )
  fake_command_lines = {
      'browser_tests': [
          './%s' % 'browser_tests', '--fake-without-patch-flag',
          '--fake-log-file', '$ISOLATED_OUTDIR/fake.log'
      ]
  }

  def is_subsequence(containing, contained):
    containing_str = ' '.join(containing)
    contained_str = ' '.join(contained)
    return contained_str in containing_str

  yield api.test(
      'without_patch_tests_contain_command_lines_from_without_patch_compilator',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          **{
              '$build/chromium_orchestrator':
                  InputProperties(
                      compilator='linux-rel-compilator',
                      compilator_watcher_git_revision='e841fc',
                  ),
          }),
      api.chromium_orchestrator.fake_head_revision(),
      api.chromium_orchestrator.override_test_spec(
          tests=['browser_tests', 'content_unittests']),
      api.chromium_orchestrator.override_compilator_steps(
          tests=['browser_tests', 'content_unittests']),
      api.chromium_orchestrator.override_compilator_steps(
          with_patch=True, is_swarming_phase=False),
      api.chromium_orchestrator.override_compilator_steps(with_patch=False),
      api.step_data('read command lines (2)',
                    api.file.read_json(fake_command_lines)),
      api.override_step_data(
          'content_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'content_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(True), failure=False)),
      api.override_step_data(
          'browser_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'browser_tests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'browser_tests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
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
      api.post_process(post_process.MustRun, 'FindIt Flakiness'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
