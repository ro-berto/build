# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Triggers compilator and tests"""

from recipe_engine import post_process
from PB.recipes.build.chromium.orchestrator import InputProperties
from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc
from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import (builds_service as
                                                       builds_service_pb2)
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from PB.recipe_engine import result as result_pb2
from google.protobuf import json_format
from google.protobuf import struct_pb2
from RECIPE_MODULES.build.chromium_tests.api import (
    ALL_TEST_BINARIES_ISOLATE_NAME)
from RECIPE_MODULES.depot_tools.tryserver import api as tryserver

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'builder_group',
    'chromium',
    'chromium_checkout',
    'chromium_swarming',
    'chromium_tests',
    'chromium_tests_builder_config',
    'code_coverage',
    'depot_tools/gclient',
    'depot_tools/gitiles',
    'depot_tools/tryserver',
    'isolate',
    'profiles',
    'recipe_engine/buildbucket',
    'recipe_engine/cas',
    'recipe_engine/cipd',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'recipe_engine/swarming',
    'recipe_engine/time',
    'test_utils',
]

PROPERTIES = InputProperties


# TODO (kimstephanie): break up RunSteps into separate methods for each phase
# of the build
def RunSteps(api, properties):
  api.path.mock_add_paths(
      api.profiles.profile_dir().join('overall-merged.profdata'))

  if not properties.compilator:
    raise api.step.InfraFailure('Missing compilator input')

  # CrOS CQ supports linking & testing CLs across different repos in one
  # build via the `Cq-Depends` footer. But Chrome's CQ does not. So check
  # if the CL author has mistakenly added the footer to their chromium CL
  # and fail loudly in that case to avoid confusion.
  if api.tryserver.is_tryserver:
    cq_depends_footer = api.tryserver.get_footer(
        api.tryserver.constants.CQ_DEPEND_FOOTER)
    if cq_depends_footer:
      raise api.step.StepFailure(
          'Commit message footer {} is not supported on Chrome builders. '
          'Please remove the line(s) from the commit message and try '
          'again.'.format(api.tryserver.constants.CQ_DEPEND_FOOTER))

  with api.chromium.chromium_layout():
    # Get current revision at HEAD of branch
    # TODO (gbeaty): To support downstream CLs, we need to find the revision
    # of the root solution, not the repo of the CL
    ref = api.tryserver.gerrit_change_target_ref

    head_revision, _ = api.gitiles.log(
        api.tryserver.gerrit_change_repo_url,
        ref,
        limit=1,
        step_name='read src HEAD revision at {}'.format(ref))
    head_revision = head_revision[0]['commit']

    gitiles_commit = common_pb.GitilesCommit(
        host=api.tryserver.gerrit_change_repo_host,
        project=api.tryserver.gerrit_change.project,
        ref=ref,
        id=head_revision)

    # Scheduled build inherits current build's project and bucket
    request = api.buildbucket.schedule_request(
        builder=properties.compilator,
        swarming_parent_run_id=api.swarming.task_id,
        properties={
            'orchestrator': {
                'builder_name': api.buildbucket.builder_name,
                'builder_group': api.builder_group.for_current
            }
        },
        gitiles_commit=gitiles_commit,
        tags=api.buildbucket.tags(**{'hide-in-gerrit': 'pointless'}))

    build = api.buildbucket.schedule(
        [request], step_name='trigger compilator (with patch)')[0]

    builder_id, builder_config = (
        api.chromium_tests_builder_config.lookup_builder())

    api.chromium_tests.configure_build(builder_config)
    # Set api.chromium.c.compile_py.compiler to empty string so that
    # prepare_checkout() does not attempt to run ensure_goma()
    api.chromium.c.compile_py.compiler = ''
    api.chromium_tests.report_builders(builder_config)

    api.chromium.apply_config('trybot_flavor')
    api.gclient.c.revisions['src'] = head_revision
    bot_update_step, targets_config = api.chromium_tests.prepare_checkout(
        builder_config,
        timeout=3600,
        set_output_commit=builder_config.set_output_commit,
        enforce_fetch=True,
        no_fetch_tags=True,
        refs=[ref])

    affected_files = api.chromium_checkout.get_files_affected_by_patch(
        report_via_property=True)
    is_deps_only_change = affected_files == ["DEPS"]
    affected_files = (
        api.chromium_tests.revise_affected_files_for_deps_autorolls(
            affected_files))

    # Must happen before without patch steps.
    if api.code_coverage.using_coverage:
      api.code_coverage.instrument(
          affected_files, is_deps_only_change=is_deps_only_change)

    def launch_compilator_watcher(build, is_swarming_phase, with_patch):
      git_revision = properties.compilator_watcher_git_revision
      cipd_pkg = 'infra/chromium/compilator_watcher/${platform}'
      if git_revision:
        version = 'git_revision:{}'.format(git_revision)
      else:
        version = 'latest'
      exe = api.m.cipd.ensure_tool(cipd_pkg, version)

      sub_build = build_pb2.Build()
      sub_build.CopyFrom(build)
      cmd = [
          exe,
          '--',
          '-compilator-id',
          build.id,
      ]
      if is_swarming_phase:
        cmd.append('-get-swarming-trigger-props')
      else:
        cmd.append('-get-local-tests')

      if with_patch:
        name = 'compilator steps (with patch)'
      else:
        name = 'compilator steps (without patch)'
      build_url = api.buildbucket.build_url(build_id=build.id)
      try:
        ret = api.step.sub_build(name, cmd, sub_build)
        ret.presentation.links['compilator build: ' + str(build.id)] = build_url
        return ret.step.sub_build
      except api.step.StepFailure:
        ret = api.step.active_result
        ret.presentation.links['compilator build: ' + str(build.id)] = build_url
        sub_build = ret.step.sub_build
        if not sub_build:
          raise api.step.InfraFailure('sub_build missing from step')
        return sub_build

    def process_sub_build(sub_build, is_swarming_phase, with_patch):

      # This condition should be rare as swarming only propagates
      # cancelations from parent -> child
      if sub_build.status == common_pb.CANCELED:
        raise api.step.InfraFailure('Compilator was canceled')

      swarming_prop_key = 'swarming_trigger_properties'
      if is_swarming_phase and swarming_prop_key in sub_build.output.properties:
        return sub_build.output.properties[swarming_prop_key], None

      if not with_patch and sub_build.status == common_pb.SUCCESS:
        raise api.step.InfraFailure(
            'Missing swarming_trigger_properties from without patch '
            'compilator')

      return None, result_pb2.RawResult(
          status=sub_build.status, summary_markdown=sub_build.summary_markdown)

    sub_build = launch_compilator_watcher(
        build, is_swarming_phase=True, with_patch=True)

    swarming_props, maybe_raw_result = process_sub_build(
        sub_build, is_swarming_phase=True, with_patch=True)

    # Can be either SUCCESS or FAILURE/INFRA_FAILURE result
    # SUCCESS means that there's no swarming tests to trigger
    if maybe_raw_result != None:
      return maybe_raw_result

    def process_swarming_props(swarming_props, builder_config, targets_config):
      swarming_digest = swarming_props['swarming_command_lines_digest']
      swarming_cwd = swarming_props['swarming_command_lines_cwd']

      swarm_hashes = swarming_props['swarm_hashes']
      swarm_hashes = dict(zip(swarm_hashes.keys(), swarm_hashes.values()))
      api.isolate.set_isolated_tests(swarm_hashes)

      tests = [
          t for t in targets_config.all_tests
          if t.uses_isolate and t.target_name in api.isolate.isolated_tests
      ]
      api.chromium_tests.download_command_lines_for_tests(
          tests,
          builder_config,
          swarming_command_lines_digest=swarming_digest,
          swarming_command_lines_cwd=swarming_cwd)
      return tests

    tests = process_swarming_props(swarming_props, builder_config,
                                   targets_config)

    api.chromium_tests.configure_swarming(
        api.tryserver.is_tryserver, builder_group=builder_id.group)

    if api.code_coverage.using_coverage:
      api.file.ensure_directory('ensure output directory',
                                api.chromium.output_dir)
      api.cas.download(
          'downloading cas digest {}'.format(ALL_TEST_BINARIES_ISOLATE_NAME),
          api.isolate.isolated_tests[ALL_TEST_BINARIES_ISOLATE_NAME],
          api.chromium.output_dir,
      )

    with api.chromium_tests.wrap_chromium_tests(builder_config, tests):
      _, failing_test_suites = (
          api.test_utils.run_tests_with_patch(
              api.chromium_tests.m,
              tests,
              retry_failed_shards=builder_config.retry_failed_shards))

      if api.code_coverage.using_coverage:
        api.code_coverage.process_coverage_data(tests)

    # Check to make sure the compilator completed any local scripts/tests
    local_tests_sub_build = launch_compilator_watcher(
        build, is_swarming_phase=False, with_patch=True)

    _, local_tests_raw_result = process_sub_build(
        local_tests_sub_build, is_swarming_phase=False, with_patch=True)

    def report_stats_and_flakiness(tests):
      api.chromium_swarming.report_stats()
      api.test_utils.summarize_findit_flakiness(api.chromium_tests.m, tests)

    def handle_failed_with_patch_tests(tests, failed_test_suites):
      report_stats_and_flakiness(tests)

      api.chromium_tests.handle_invalid_test_suites(failing_test_suites)
      api.chromium_tests.summarize_test_failures(tests)

    if not failing_test_suites:
      report_stats_and_flakiness(tests)
      return local_tests_raw_result

    if api.chromium_tests.should_skip_without_patch(builder_config,
                                                    affected_files):
      handle_failed_with_patch_tests(tests, failing_test_suites)

      summary_markdown = api.chromium_tests._format_unrecoverable_failures(
          failing_test_suites, 'with patch')
      if (local_tests_raw_result and
          local_tests_raw_result.status != common_pb.SUCCESS):
        summary_markdown += '\n\n From compilator:\n{}'.format(
            local_tests_raw_result.summary_markdown)

      return result_pb2.RawResult(
          summary_markdown=summary_markdown, status=common_pb.FAILURE)

    # without patch phase
    request = api.buildbucket.schedule_request(
        builder=properties.compilator,
        swarming_parent_run_id=api.swarming.task_id,
        properties={
            'orchestrator': {
                'builder_name': api.buildbucket.builder_name,
                'builder_group': api.builder_group.for_current
            },
            'swarming_targets':
                list(set(t.target_name for t in failing_test_suites)),
        },
        gitiles_commit=gitiles_commit,
        tags=api.buildbucket.tags(**{'hide-in-gerrit': 'pointless'}))

    wo_build = api.buildbucket.schedule(
        [request], step_name='trigger compilator (without patch)')[0]

    api.chromium_tests.deapply_patch(bot_update_step)
    targets_config = api.chromium_tests.create_targets_config(
        builder_config, bot_update_step)

    sub_build = launch_compilator_watcher(
        wo_build, is_swarming_phase=True, with_patch=False)
    swarming_props, maybe_raw_result = process_sub_build(
        sub_build, is_swarming_phase=True, with_patch=False)

    # FAILURE/INFRA_FAILURE result
    if maybe_raw_result != None:
      handle_failed_with_patch_tests(tests, failing_test_suites)
      return maybe_raw_result

    process_swarming_props(swarming_props, builder_config, targets_config)

    with api.chromium_tests.wrap_chromium_tests(builder_config,
                                                failing_test_suites):
      api.test_utils.run_tests(
          api.chromium_tests.m,
          failing_test_suites,
          'without patch',
          sort_by_shard=True)

    # unrecoverable_test_suites are those that passed without a patch, so the
    # failures must be due to the CL
    unrecoverable_test_suites = api.chromium_tests.summarize_test_failures(
        tests, retried_without_patch_suites=failing_test_suites)

    report_stats_and_flakiness(tests)

    summary_markdown = ''
    final_status = common_pb.SUCCESS

    if unrecoverable_test_suites:
      api.chromium_tests.handle_invalid_test_suites(unrecoverable_test_suites)
      summary_markdown += api.chromium_tests._format_unrecoverable_failures(
          unrecoverable_test_suites, 'with patch')
      final_status = common_pb.FAILURE

    if (local_tests_raw_result and
        local_tests_raw_result.status != common_pb.SUCCESS):
      summary_markdown += '\n\n From compilator:\n{}'.format(
          local_tests_raw_result.summary_markdown)
      if final_status == common_pb.SUCCESS:
        final_status = local_tests_raw_result.status

    return result_pb2.RawResult(
        summary_markdown=summary_markdown, status=final_status)


def GenTests(api):

  def override_test_spec(tests=None):
    tests = tests or ['browser_tests']
    gtest_tests = [{
        'name': test,
        'swarming': {
            'can_use_on_swarming_builders': True
        },
        'isolate_coverage_data': True,
    } for test in tests]
    return api.chromium_tests.read_source_side_spec(
        'chromium.linux', {
            'Linux Builder': {
                'scripts': [{
                    "isolate_profile_data": True,
                    "name": "check_static_initializers",
                    "script": "check_static_initializers.py",
                    "swarming": {}
                }],
            },
            'Linux Tests': {
                'gtest_tests': gtest_tests
            },
        })

  build_id = 1234
  fake_command_lines_digest = (
      'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855/0')

  def get_fake_swarming_trigger_properties(tests):
    input_hash = (
        '797e944dad5241e7fe111cfd01e45f02e2f4937dd34b248603e603d2948e174e/1298')
    swarm_hashes = {test: input_hash for test in tests}
    swarm_hashes[ALL_TEST_BINARIES_ISOLATE_NAME] = input_hash
    return {
        'swarming_command_lines_digest': fake_command_lines_digest,
        'swarming_command_lines_cwd': 'out/Release',
        'swarm_hashes': swarm_hashes,
    }

  def override_trigger_compilator(with_patch=True):
    if with_patch:
      name = 'trigger compilator (with patch)'
    else:
      name = 'trigger compilator (without patch)'
    return api.buildbucket.simulated_schedule_output(
        builds_service_pb2.BatchResponse(
            responses=[dict(schedule_build=build_pb2.Build(id=build_id))]),
        step_name=name)

  def override_compilator_steps(comp_build_id=1234,
                                sub_build_status=common_pb.SUCCESS,
                                sub_build_summary='',
                                empty_props=False,
                                is_swarming_phase=True,
                                with_patch=True,
                                tests=None):
    tests = tests or ['browser_tests']
    output_json_obj = {}
    if is_swarming_phase:
      if not empty_props:
        output_json_obj = {
            'swarming_trigger_properties':
                get_fake_swarming_trigger_properties(tests)
        }

    sub_build = build_pb2.Build(
        id=54321,
        status=sub_build_status,
        summary_markdown=sub_build_summary,
        output=dict(
            properties=json_format.Parse(
                api.json.dumps(output_json_obj), struct_pb2.Struct())))
    if with_patch:
      name = 'compilator steps (with patch)'
    else:
      name = 'compilator steps (without patch)'
    if not is_swarming_phase:
      name += ' (2)'
    return api.override_step_data(
        name,
        api.step.sub_build(sub_build),
    )

  def fake_head_revision(ref='refs/heads/main'):
    return api.step_data('read src HEAD revision at {}'.format(ref),
                         api.gitiles.make_log_test_data('deadbeef'))

  yield api.test(
      'basic',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(
          InputProperties(
              compilator='linux-rel-compilator',
              compilator_watcher_git_revision='e841fc',
          )),
      api.code_coverage(use_clang_coverage=True),
      override_compilator_steps(),
      override_compilator_steps(is_swarming_phase=False),
      override_trigger_compilator(),
      fake_head_revision(),
      api.post_process(post_process.StepCommandContains, 'bot_update',
                       ['--refs', 'refs/heads/main']),
      api.post_process(post_process.StepCommandContains, 'bot_update',
                       ['--patch_ref']),
      override_test_spec(),
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
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      api.tryserver.gerrit_change_target_ref('refs/branch-heads/4472'),
      api.code_coverage(use_clang_coverage=True),
      fake_head_revision('refs/branch-heads/4472'),
      override_test_spec(),
      override_compilator_steps(),
      override_compilator_steps(is_swarming_phase=False),
      override_trigger_compilator(),
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
      'missing_compilator_watcher_git_revision',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      api.code_coverage(use_clang_coverage=True),
      override_compilator_steps(),
      override_compilator_steps(is_swarming_phase=False),
      override_trigger_compilator(),
      fake_head_revision(),
      override_test_spec(),
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
      'no_tests_to_trigger',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      fake_head_revision(),
      override_test_spec(),
      override_trigger_compilator(),
      override_compilator_steps(empty_props=True),
      api.post_process(post_process.MustRun, 'trigger compilator (with patch)'),
      api.post_process(post_process.DoesNotRun, 'browser_tests (with patch)'),
      api.post_process(post_process.LogContains,
                       'trigger compilator (with patch)', 'request',
                       ['tryserver.chromium.linux', 'linux-rel-compilator']),
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
      api.properties(InputProperties(compilator='linux-rel-compilator')),
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
      'failing_test_retry_shard_passed',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      fake_head_revision(),
      override_test_spec(),
      override_trigger_compilator(),
      api.override_step_data(
          'browser_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'browser_tests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(True), failure=False)),
      override_compilator_steps(),
      override_compilator_steps(is_swarming_phase=False),
      api.post_process(post_process.MustRun, 'trigger compilator (with patch)'),
      api.post_process(post_process.DoesNotRun,
                       'trigger compilator (without patch)'),
      api.post_process(post_process.MustRun,
                       'browser_tests (retry shards with patch)'),
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.MustRun, 'FindIt Flakiness'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failing_test_retry_shard_failed_skip_without_patch',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      fake_head_revision(),
      override_test_spec(),
      override_trigger_compilator(),
      override_compilator_steps(),
      override_compilator_steps(
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
      'retry_without_patch_passes_tryjob_fails',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      fake_head_revision(),
      override_trigger_compilator(),
      override_trigger_compilator(with_patch=False),
      override_test_spec(tests=['browser_tests', 'content_unittests']),
      override_compilator_steps(tests=['browser_tests', 'content_unittests']),
      override_compilator_steps(is_swarming_phase=False),
      override_compilator_steps(with_patch=False),
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
      api.post_process(post_process.MustRun,
                       'trigger compilator (without patch)'),
      api.post_process(post_process.MustRun, 'browser_tests (without patch)'),
      api.post_process(post_process.DoesNotRun,
                       'content_unittests (without patch)'),
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.MustRun, 'FindIt Flakiness'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_without_patch_passes_local_tests_failed',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      fake_head_revision(),
      override_trigger_compilator(),
      override_trigger_compilator(with_patch=False),
      override_test_spec(tests=['browser_tests', 'content_unittests']),
      override_compilator_steps(tests=['browser_tests', 'content_unittests']),
      override_compilator_steps(
          is_swarming_phase=False,
          sub_build_summary=("1 Test Suite(s) failed.\n\n"
                             "**headless_python_unittests** failed."),
          sub_build_status=common_pb.FAILURE,
      ),
      override_compilator_steps(with_patch=False),
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
      api.post_process(post_process.MustRun,
                       'trigger compilator (without patch)'),
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
      'retry_without_patch_fails_tryjob_succeeds',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      fake_head_revision(),
      override_test_spec(tests=['browser_tests', 'content_unittests']),
      override_compilator_steps(tests=['browser_tests', 'content_unittests']),
      override_trigger_compilator(),
      override_trigger_compilator(with_patch=False),
      override_compilator_steps(with_patch=True, is_swarming_phase=False),
      override_compilator_steps(with_patch=False),
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
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.MustRun, 'FindIt Flakiness'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_without_patch_fails_tests_and_local_tests',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      fake_head_revision(),
      override_test_spec(tests=['browser_tests', 'content_unittests']),
      override_compilator_steps(tests=['browser_tests', 'content_unittests']),
      override_trigger_compilator(),
      override_trigger_compilator(with_patch=False),
      override_compilator_steps(
          is_swarming_phase=False,
          sub_build_summary=("1 Test Suite(s) failed.\n\n"
                             "**headless_python_unittests** failed."),
          sub_build_status=common_pb.FAILURE,
      ),
      override_compilator_steps(with_patch=False),
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
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      fake_head_revision(),
      override_test_spec(),
      override_trigger_compilator(),
      override_trigger_compilator(with_patch=False),
      override_compilator_steps(),
      override_compilator_steps(with_patch=True, is_swarming_phase=False),
      override_compilator_steps(with_patch=False, empty_props=True),
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
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      override_test_spec(),
      fake_head_revision(),
      override_trigger_compilator(),
      override_compilator_steps(
          sub_build_status=common_pb.FAILURE,
          empty_props=True,
          sub_build_summary='Step compile (with patch) failed.'),
      api.post_process(post_process.ResultReason,
                       'Step compile (with patch) failed.'),
      api.post_process(post_process.MustRun, 'trigger compilator (with patch)'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failed_wo_patch_compilator',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      fake_head_revision(),
      override_test_spec(),
      override_trigger_compilator(),
      override_compilator_steps(with_patch=True, is_swarming_phase=False),
      override_trigger_compilator(with_patch=False),
      override_compilator_steps(),
      override_compilator_steps(
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
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      override_test_spec(),
      fake_head_revision(),
      override_trigger_compilator(),
      override_compilator_steps(
          sub_build_status=common_pb.INFRA_FAILURE,
          empty_props=True,
          sub_build_summary='Timeout waiting for compilator build'),
      api.post_process(post_process.ResultReason,
                       'Timeout waiting for compilator build'),
      api.post_process(post_process.MustRun, 'trigger compilator (with patch)'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'canceled_compilator_while_waiting_for_swarming_props',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      override_test_spec(),
      fake_head_revision(),
      override_trigger_compilator(),
      override_compilator_steps(
          sub_build_status=common_pb.CANCELED,
          empty_props=True,
          sub_build_summary='Canceled'),
      api.post_process(post_process.MustRun, 'trigger compilator (with patch)'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'missing_sub_build_in_active_step',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      fake_head_revision(),
      override_test_spec(),
      api.override_step_data(
          'compilator steps (with patch)',
          api.step.sub_build(None),
      ),
      override_trigger_compilator(),
      api.post_process(post_process.MustRun, 'trigger compilator (with patch)'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failed_compilator_local_test',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      fake_head_revision(),
      override_test_spec(),
      override_compilator_steps(),
      override_compilator_steps(
          is_swarming_phase=False,
          sub_build_status=common_pb.FAILURE,
          sub_build_summary=("1 Test Suite(s) failed.\n\n"
                             "**headless_python_unittests** failed.")),
      override_trigger_compilator(),
      api.override_step_data(
          'browser_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'browser_tests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(True), failure=False)),
      api.post_process(post_process.MustRun, 'trigger compilator (with patch)'),
      api.post_process(post_process.MustRun, 'Tests statistics'),
      api.post_process(post_process.MustRun, 'FindIt Flakiness'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'compilator_canceled_at_local_test_phase',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      fake_head_revision(),
      override_test_spec(),
      override_compilator_steps(),
      override_compilator_steps(
          sub_build_status=common_pb.CANCELED,
          is_swarming_phase=False,
          sub_build_summary='Canceled'),
      override_compilator_steps(),
      api.post_process(post_process.MustRun, 'trigger compilator (with patch)'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'sub_build_infra_failed',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      override_test_spec(),
      fake_head_revision(),
      override_trigger_compilator(),
      override_compilator_steps(sub_build_status=common_pb.INFRA_FAILURE),
      api.post_process(post_process.MustRun, 'trigger compilator (with patch)'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'code_coverage',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      api.code_coverage(use_clang_coverage=True),
      fake_head_revision(),
      override_test_spec(),
      override_trigger_compilator(),
      override_compilator_steps(),
      override_compilator_steps(is_swarming_phase=False),
      api.post_process(post_process.MustRun, 'trigger compilator (with patch)'),
      api.post_process(post_process.LogContains,
                       'trigger compilator (with patch)', 'request',
                       ['tryserver.chromium.linux', 'linux-rel-compilator']),
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
      'code_coverage_retry_shard',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      api.code_coverage(use_clang_coverage=True),
      fake_head_revision(),
      override_test_spec(),
      override_compilator_steps(),
      override_compilator_steps(is_swarming_phase=False),
      override_trigger_compilator(),
      api.override_step_data(
          'browser_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'browser_tests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(True), failure=False)),
      api.post_process(post_process.MustRun, 'trigger compilator (with patch)'),
      api.post_process(post_process.LogContains,
                       'trigger compilator (with patch)', 'request',
                       ['tryserver.chromium.linux', 'linux-rel-compilator']),
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
