# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from google.protobuf.json_format import MessageToDict
from recipe_engine import recipe_api

from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from PB.recipe_engine import result as result_pb2
from RECIPE_MODULES.build.attr_utils import attrib, attrs, mapping, sequence
from RECIPE_MODULES.build.chromium_tests.api import (
    ALL_TEST_BINARIES_ISOLATE_NAME)

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

COMPILATOR_SWARMING_TASK_COLLECT_STEP = (
    'wait for compilator swarming task cleanup overhead')

BUILD_CANCELED_SUMMARY = 'Build was canceled.'


@attrs()
class CompilatorOutputProps(object):
  """Contains output properties from the triggered Compilator build

  Attributes:
    swarming_props: Dict containing swarming information to trigger tests
    got_revisions: Dict containing revisions checked out for src and other deps
    affected_files: List containing paths (str) of files affected by the patch
    deleted_files: List containing paths (str) of files deleted by the patch
    src_side_deps_digest: CAS digest hash (str) for downloading src-side deps
    src_side_test_spec_dir: Path (str) to downloaded src-side directory that
      contains test specs, relative to the root of the downloaded src-side deps
    skipping_coverage: Whether coverage is being skipped. The compilator
      determines this by checking the len of affected eligible files.
  """

  swarming_props = attrib(mapping[str, ...])
  got_revisions = attrib(mapping[str, str])
  affected_files = attrib(sequence[str], default=None)
  deleted_files = attrib(sequence[str], default=None)
  src_side_deps_digest = attrib(str, default=None)
  src_side_test_spec_dir = attrib(str, default=None)
  skipping_coverage = attrib(bool, default=None)


class ChromiumOrchestratorApi(recipe_api.RecipeApi):

  def __init__(self, properties, **kwargs):
    super(ChromiumOrchestratorApi, self).__init__(**kwargs)
    self.compilator = properties.compilator
    self.compilator_watcher_git_revision = (
        properties.compilator_watcher_git_revision)

    self.compilator_watcher_pkg = None

    # Buildbucket ID of most recently triggered compilator build
    # If a without patch compilator build is triggered, this will be updated
    # to the without patch compilator build's ID
    self.current_compilator_buildbucket_id = None

  def trybot_steps(self):
    # The buildbucket input gitiles_commit is populated by the bootstrapper.
    # If the builder does not use the bootstrapper, gitiles_commit will not
    # be populated.
    if self.m.buildbucket.build.input.HasField('gitiles_commit'):
      self.m.buildbucket.set_output_gitiles_commit(
          self.m.buildbucket.build.input.gitiles_commit)

    raw_result = self.test_patch()

    # If the orchestrator build is canceled or infra failed, the exception
    # should bubble up during test_patch() and the code below will not be
    # executed
    if (self.current_compilator_buildbucket_id and
        not self.m.runtime.in_global_shutdown):
      comp_build = self.m.buildbucket.get(
          step_name='fetch compilator build proto',
          build_id=self.current_compilator_buildbucket_id)

      # test_patch() waits for the compilator build to finish
      # so this assertion should always be True.
      # If there is some regression that changes this, this prevents the
      # orchestrator build from waiting for an unfinished compilator build
      assert comp_build.status & common_pb.ENDED_MASK
      # crbug.com/1271287#c22
      # Wait for compilator task overhead to complete
      self.m.swarming.collect(
          name=COMPILATOR_SWARMING_TASK_COLLECT_STEP,
          tasks=[comp_build.infra.swarming.task_id],
          timeout="3m")

    return raw_result

  # TODO (kimstephanie): break up test_patch into separate methods for each
  # phase of the build
  def test_patch(self):
    """Runs steps to test CL changes

    Returns:
      RawResult object or None
    """
    if not self.compilator:
      raise self.m.step.InfraFailure('Missing compilator input')

    self.m.chromium_tests.raise_failure_if_cq_depends_footer_exists()

    builder_id, builder_config = self.configure_build()

    experiments = self.m.buildbucket.build.input.experiments
    remove_src_checkout_experiment = (
        'remove_src_checkout_experiment' in experiments)

    # Trigger compilator to compile and build targets with patch
    # Scheduled build inherits current build's project and bucket
    compilator_properties = {
        'orchestrator': {
            'builder_name': self.m.buildbucket.builder_name,
            'builder_group': self.m.builder_group.for_current
        }
    }

    gitiles_commit = None
    root_solution_revision = None
    patch_repo_head_revision = None

    if not remove_src_checkout_experiment:
      patch_repo_ref = self.m.tryserver.gerrit_change_target_ref
      gerrit_change_project = self.m.tryserver.gerrit_change.project

      if gerrit_change_project == 'chromium/src':
        # Usually refs/heads/main for ToT CLs, but can be branch heads for
        # branch CLs
        src_ref = patch_repo_ref
      else:
        # This assumes that non chromium/src projects only runs builds on
        # the main branch of src.
        src_ref = 'refs/heads/main'

      src_head_revision, _ = self.m.gitiles.log(
          'https://chromium.googlesource.com/chromium/src',
          src_ref,
          limit=1,
          step_name='read src HEAD revision at {}'.format(src_ref))
      src_head_revision = src_head_revision[0]['commit']

      gclient_soln_name = self.m.gclient.get_repo_path(
          self.m.tryserver.gerrit_change_repo_url)

      if gerrit_change_project == 'chromium/src':
        patch_repo_head_revision = src_head_revision
        gitiles_commit = common_pb.GitilesCommit(
            host=self.m.tryserver.gerrit_change_repo_host,
            project=self.m.tryserver.gerrit_change.project,
            ref=src_ref,
            id=src_head_revision)
      else:
        patch_repo_head_revision, _ = self.m.gitiles.log(
            self.m.tryserver.gerrit_change_repo_url,
            patch_repo_ref,
            limit=1,
            step_name='read {} HEAD revision at {}'.format(
                gerrit_change_project, patch_repo_ref))
        patch_repo_head_revision = patch_repo_head_revision[0]['commit']
        root_solution_revision = src_head_revision

        compilator_properties['root_solution_revision'] = root_solution_revision
        compilator_properties['deps_revision_overrides'] = {
            gclient_soln_name: patch_repo_head_revision
        }

      self.m.gclient.c.revisions[gclient_soln_name] = patch_repo_head_revision

    # Pass in any RTS mode input props
    compilator_properties.update(self.m.cq.props_for_child_build)
    if remove_src_checkout_experiment:
      self.m.chromium_bootstrap.update_trigger_properties(compilator_properties)

    request = self.m.buildbucket.schedule_request(
        builder=self.compilator,
        swarming_parent_run_id=self.m.swarming.task_id,
        properties=compilator_properties,
        gitiles_commit=gitiles_commit,
        tags=self.m.buildbucket.tags(**{'hide-in-gerrit': 'pointless'}),
        experiments={
            'remove_src_checkout_experiment': remove_src_checkout_experiment
        })

    build = self.m.buildbucket.schedule(
        [request], step_name='trigger compilator (with patch)')[0]

    self.current_compilator_buildbucket_id = build.id

    if not remove_src_checkout_experiment:
      bot_update_step, targets_config = self.m.chromium_tests.prepare_checkout(
          builder_config,
          timeout=3600,
          enforce_fetch=True,
          no_fetch_tags=True,
          root_solution_revision=root_solution_revision,
          refs=[patch_repo_ref])

    # Now that we've finished the Orchestrator's bot_update and analyze, let's
    # check on the triggered compilator and display its steps (until it
    # outputs the swarming trigger props).
    sub_build = self.launch_compilator_watcher(
        build, is_swarming_phase=True, with_patch=True)

    comp_output, maybe_raw_result = self.process_sub_build(
        sub_build, is_swarming_phase=True, with_patch=True)

    # Can be either SUCCESS or FAILURE/INFRA_FAILURE result
    # SUCCESS means that there's no swarming tests to trigger
    if maybe_raw_result != None:
      return maybe_raw_result

    if remove_src_checkout_experiment:
      self.m.chromium_checkout.checkout_dir = self.m.path['cleanup']

      self.m.cas.download(
          'download src-side deps',
          comp_output.src_side_deps_digest,
          self.m.chromium_checkout.src_dir,
      )

      affected_files = comp_output.affected_files
      targets_config = self.m.chromium_tests.create_targets_config(
          builder_config,
          comp_output.got_revisions,
          self.m.chromium_checkout.src_dir,
          source_side_spec_dir=self.m.chromium_checkout.src_dir.join(
              comp_output.src_side_test_spec_dir),
          isolated_tests_only=True)
      self.check_for_non_swarmed_isolated_tests(targets_config.all_tests)
      # This is used to set build properties on swarming tasks
      self.m.chromium.set_build_properties(comp_output.got_revisions)
    else:
      affected_files = self.m.chromium_checkout.get_files_affected_by_patch(
          report_via_property=True)

    # Now let's get all the tests ready with the swarming trigger info
    # outputed by the compilator
    tests = self.process_swarming_props(comp_output.swarming_props,
                                        builder_config, targets_config)

    self.m.chromium_tests.configure_swarming(
        self.m.tryserver.is_tryserver, builder_group=builder_id.group)

    if (self.m.code_coverage.using_coverage and
        not comp_output.skipping_coverage):
      self.m.code_coverage.set_is_per_cl_coverage(True)
      self.m.code_coverage.filter_and_set_eligible_files(affected_files)

      output_dir = self.m.chromium_checkout.src_dir.join(
          'out', self.m.chromium.c.build_config_fs)
      self.m.code_coverage.build_dir = output_dir

      # TODO(crbug/1287228): Remove once all orchestrators have
      # remove_src_checkout_experiment enabled
      # cas download raises "file exists" errors for android's json files
      if not remove_src_checkout_experiment:
        self.m.file.rmcontents('clear out output directory', output_dir)

      self.m.file.ensure_directory('ensure output directory', output_dir)
      self.m.cas.download(
          'downloading cas digest {}'.format(ALL_TEST_BINARIES_ISOLATE_NAME),
          self.m.isolate.isolated_tests[ALL_TEST_BINARIES_ISOLATE_NAME],
          output_dir,
      )

      if self.m.code_coverage.use_clang_coverage:
        clang_update_script = self.m.chromium_checkout.src_dir.join(
            'tools', 'clang', 'scripts', 'update.py')
        args = ['python3', clang_update_script, '--package', 'coverage_tools']
        self.m.step(
            'run tools/clang/scripts/update.py',
            args,
        )

    # Trigger and wait for the tests (and process coverage data, if enabled)!
    with self.m.chromium_tests.wrap_chromium_tests(builder_config, tests):
      invalid_test_suites, failing_test_suites = (
          self.m.test_utils.run_tests_with_patch(
              tests,
              retry_failed_shards=builder_config.retry_failed_shards))

      if (self.m.code_coverage.using_coverage and
          not comp_output.skipping_coverage):
        self.m.code_coverage.process_coverage_data(tests)

    # Let's check back on the compilator to see the results of the local
    # scripts/tests. The sub_build will only display steps relevant to those
    # local scripts/tests.
    local_tests_sub_build = self.launch_compilator_watcher(
        build, is_swarming_phase=False, with_patch=True)

    _, local_tests_raw_result = self.process_sub_build(
        local_tests_sub_build, is_swarming_phase=False, with_patch=True)

    if not failing_test_suites:
      self.report_stats_and_flakiness(tests)
      # There could be exonerated failed tests from FindIt flakes
      self.m.chromium_tests.summarize_test_failures(tests)

      # Checks for new flaky tests are run on both the orchestrator and
      # compilator for CQ builders that have flaky checks enabled.
      if self.m.flakiness.check_for_flakiness:
        new_tests = self.m.flakiness.find_tests_for_flakiness(
            tests, affected_files=affected_files)
        if new_tests:
          result = self.m.chromium_tests.run_tests_for_flakiness(
              builder_config, new_tests)

          # If the swarming checks for flakiness succeed, we'll only need to
          # check for the compilator's failures. On success, None is returned by
          # run_tests_for_flakiness(). Otherwise, aggregate the summaries s.t.
          # all flaky results can be presented to the user.
          if not result:
            return local_tests_raw_result

          if (local_tests_raw_result and
              local_tests_raw_result.status != common_pb.SUCCESS):
            summary = result.summary_markdown
            summary += '\n\n From compilator:\n {}'.format(
                local_tests_raw_result.summary_markdown)
            result.summary_markdown = summary
          return result

      # All of the swarming tests passed, so the final status of the tryjob
      # depends on whether the local tests run by the compilator passed or not.
      return local_tests_raw_result

    # Exit without retry without patch if there were invalid tests or
    # (without patch) should be skipped
    if invalid_test_suites or self.m.chromium_tests.should_skip_without_patch(
        builder_config, affected_files,
        self.m.chromium_checkout.src_dir.join(
            comp_output.src_side_test_spec_dir)):
      self.handle_failed_with_patch_tests(tests, failing_test_suites)

      summary_markdown = self.m.chromium_tests._format_unrecoverable_failures(
          failing_test_suites, 'with patch')
      if (local_tests_raw_result and
          local_tests_raw_result.status != common_pb.SUCCESS):
        summary_markdown += '\n\n From compilator:\n{}'.format(
            local_tests_raw_result.summary_markdown)

      return result_pb2.RawResult(
          summary_markdown=summary_markdown, status=common_pb.FAILURE)

    # =====================================================================
    # Now we're going into the without patch phase
    # =====================================================================

    # Trigger another compilator build with the targets needed
    compilator_properties['swarming_targets'] = list(
        set(t.target_name for t in failing_test_suites))

    request = self.m.buildbucket.schedule_request(
        builder=self.compilator,
        swarming_parent_run_id=self.m.swarming.task_id,
        properties=compilator_properties,
        gitiles_commit=gitiles_commit,
        tags=self.m.buildbucket.tags(**{'hide-in-gerrit': 'pointless'}),
        experiments={
            'remove_src_checkout_experiment': remove_src_checkout_experiment
        })

    wo_build = self.m.buildbucket.schedule(
        [request], step_name='trigger compilator (without patch)')[0]

    self.current_compilator_buildbucket_id = wo_build.id

    if not remove_src_checkout_experiment:
      self.m.chromium_tests.deapply_patch(bot_update_step)

    # Display steps of triggered (without patch) compilator until it outputs
    # swarming trigger props for the tests to retrigger without patch
    sub_build = self.launch_compilator_watcher(
        wo_build, is_swarming_phase=True, with_patch=False)
    comp_output, maybe_raw_result = self.process_sub_build(
        sub_build, is_swarming_phase=True, with_patch=False)

    # FAILURE/INFRA_FAILURE result
    if maybe_raw_result != None:
      self.handle_failed_with_patch_tests(tests, failing_test_suites)
      return maybe_raw_result

    self.process_swarming_props(
        comp_output.swarming_props, builder_config, targets_config, tests=tests)

    # Trigger and wait for the (without patch) tests!
    with self.m.chromium_tests.wrap_chromium_tests(builder_config,
                                                   failing_test_suites):
      self.m.test_utils.run_tests(
          failing_test_suites,
          'without patch',
          sort_by_shard=True)

    # unrecoverable_test_suites are those that passed without a patch, so the
    # failures must be due to the CL
    unrecoverable_test_suites = self.m.chromium_tests.summarize_test_failures(
        tests, retried_without_patch_suites=failing_test_suites)

    self.report_stats_and_flakiness(tests)

    summary_markdown = ''
    final_status = common_pb.SUCCESS

    if unrecoverable_test_suites:
      self.m.chromium_tests.handle_invalid_test_suites(
          unrecoverable_test_suites)
      summary_markdown += self.m.chromium_tests._format_unrecoverable_failures(
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

  def configure_build(self):
    builder_id, builder_config = (
        self.m.chromium_tests_builder_config.lookup_builder())

    use_rts = self.m.chromium_tests.get_quickrun_options(builder_config)
    self.m.chromium_tests.configure_build(
        builder_config, use_rts, test_only=True)

    # Set self.m.chromium.c.compile_py.compiler to empty string so that
    # prepare_checkout() does not attempt to run ensure_goma()
    self.m.chromium.c.compile_py.compiler = ''
    self.m.chromium_tests.report_builders(builder_config)
    self.m.chromium_tests.print_link_to_results()

    self.m.chromium.apply_config('trybot_flavor')
    return builder_id, builder_config

  def launch_compilator_watcher(self, build, is_swarming_phase, with_patch):
    """Launches a sub_build displaying a subset of the Compilator's steps

    Args:
      build (Build): buildbucket Build of triggered Compilator
      is_swarming_phase (bool): whether the Orchestrator is currently waiting
        for swarming props or not
      with_patch (bool): whether the Orchestrator is currently using a patch or
        not

    Returns:
      Build proto of sub_build
    """
    if not self.compilator_watcher_pkg:
      git_revision = self.compilator_watcher_git_revision
      cipd_pkg = 'infra/chromium/compilator_watcher/${platform}'
      if git_revision:
        version = 'git_revision:{}'.format(git_revision)
      else:
        version = 'latest'
      self.compilator_watcher_pkg = self.m.cipd.ensure_tool(cipd_pkg, version)

    sub_build = build_pb2.Build()
    sub_build.CopyFrom(build)
    cmd = [
        self.compilator_watcher_pkg,
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
    build_url = self.m.buildbucket.build_url(build_id=build.id)
    try:
      ret = self.m.step.sub_build(name, cmd, sub_build)
      ret.presentation.links['compilator build: ' + str(build.id)] = build_url
      return ret.step.sub_build
    except self.m.step.StepFailure:
      ret = self.m.step.active_result
      ret.presentation.links['compilator build: ' + str(build.id)] = build_url
      sub_build = ret.step.sub_build
      if not sub_build:
        raise self.m.step.InfraFailure('sub_build missing from step')
      return sub_build

  def process_sub_build(self, sub_build, is_swarming_phase, with_patch):
    """Processes the sub_build's status and output properties

    Args:
      sub_build (Build): completed sub_build that displayed Compilator steps
      is_swarming_phase (bool): whether the Orchestrator is currently waiting
        for swarming props or not
      with_patch (bool): whether the Orchestrator is currently using a patch or
        not

    Returns tuple of:
      CompilatorOutputProps or None
      RawResult object or None
    """
    # This condition should be rare as swarming only propagates
    # cancelations from parent -> child
    if sub_build.status == common_pb.CANCELED:
      if self.m.runtime.in_global_shutdown:
        return None, result_pb2.RawResult(
            status=common_pb.CANCELED, summary_markdown=BUILD_CANCELED_SUMMARY)
      raise self.m.step.InfraFailure(
          'Compilator was canceled before the parent orchestrator was canceled.'
      )

    swarming_prop_key = 'swarming_trigger_properties'
    if is_swarming_phase and swarming_prop_key in sub_build.output.properties:
      output_props = MessageToDict(sub_build.output.properties)

      got_revisions = {k: v for k, v in output_props.items() if 'got_' in k}

      affected_files = None
      if 'affected_files' in output_props:
        affected_files = self.m.chromium_checkout.format_affected_file_paths(
            output_props['affected_files']['first_100'])

      # TODO (kimstephanie): Replace deleted_files and src_side_.* with
      # output_props.get() in a separate CL
      deleted_files = None
      if 'deleted_files' in output_props:
        deleted_files = output_props['deleted_files']

      src_side_deps_digest = None
      src_side_test_spec_dir = None
      if 'src_side_deps_digest' in output_props:
        src_side_deps_digest = output_props['src_side_deps_digest']
        src_side_test_spec_dir = output_props['src_side_test_spec_dir']

      comp_output = CompilatorOutputProps(
          swarming_props=output_props[swarming_prop_key],
          got_revisions=got_revisions,
          affected_files=affected_files,
          deleted_files=deleted_files,
          src_side_deps_digest=src_side_deps_digest,
          src_side_test_spec_dir=src_side_test_spec_dir,
          skipping_coverage=output_props.get('skipping_coverage'),
      )
      return comp_output, None

    if not with_patch and sub_build.status == common_pb.SUCCESS:
      raise self.m.step.InfraFailure(
          'Missing swarming_trigger_properties from without patch '
          'compilator')

    return None, result_pb2.RawResult(
        status=sub_build.status, summary_markdown=sub_build.summary_markdown)

  def process_swarming_props(self,
                             swarming_props,
                             builder_config,
                             targets_config,
                             tests=None):
    """Read isolate hashes swarming_props content and download command lines

    Args:
      swarming_props (dict): contains information about swarming tests to
        trigger
      builder_config (BuilderConfig): configuration for the Orchestrator
        builder
      targets_config (TargetsConfig): configuration for the tests' targets
      tests (list(Test)): Test objects to update with swarming info. If None,
        new Test objects will be created.
    Returns:
      List of Test objects with swarming info
    """
    swarming_digest = swarming_props['swarming_command_lines_digest']
    swarming_cwd = swarming_props['swarming_command_lines_cwd']

    swarm_hashes = dict(swarming_props['swarm_hashes'])
    self.m.isolate.set_isolated_tests(swarm_hashes)

    if not tests:
      tests = [
          t for t in targets_config.all_tests
          if t.uses_isolate and t.target_name in self.m.isolate.isolated_tests
      ]

    # CLs that update the test command lines are actually blocked from
    # running a without patch step, so the command lines aren't actually
    # updated to anything different.
    self.m.chromium_tests.download_command_lines_for_tests(
        tests,
        builder_config,
        swarming_command_lines_digest=swarming_digest,
        swarming_command_lines_cwd=swarming_cwd)
    return tests

  def report_stats_and_flakiness(self, tests):
    self.m.chromium_swarming.report_stats()
    self.m.test_utils.summarize_findit_flakiness(tests)

  def handle_failed_with_patch_tests(self, tests, failing_test_suites):
    """Summarizes test stats, flakiness, and test failures

    Args:
      tests: Test objects of completed tests
      failing_test_suites: Test objects of failed tests. Subset of 'tests' arg
    """
    self.report_stats_and_flakiness(tests)
    self.m.chromium_tests.summarize_test_failures(tests)
    self.m.chromium_tests.handle_invalid_test_suites(failing_test_suites)

  def check_for_non_swarmed_isolated_tests(self, tests):
    for t in tests:
      if t.uses_isolate and not t.runs_on_swarming:
        raise self.m.step.StepFailure(
            '{} is an isolated test but is not swarmed.'.format(t.target_name))
