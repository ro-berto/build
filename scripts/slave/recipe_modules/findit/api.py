# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from collections import defaultdict
import json
import re

from recipe_engine import recipe_api
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from RECIPE_MODULES.build.chromium_tests import bot_spec, steps

# This has no special meaning, just a placeholder for expectations data.
_GIT_LS_REMOTE_OUTPUT = ('1234567123456712345671234567888812345678'
                         '\trefs/heads/master')
_GIT_REV_PARSE_OUTPUT = '1234567123456712345671234567888812345678'


class FinditApi(recipe_api.RecipeApi):
  class TestResult(object):
    SKIPPED = 'skipped'  # A commit doesn't impact the test.
    PASSED = 'passed'  # The compile or test passed.
    FAILED = 'failed'  # The compile or test failed.
    INFRA_FAILED = 'infra_failed'  # Infra failed.

  def get_bot_mirror_for_tester(self, tester_id, builders):
    tester_spec = builders[tester_id]

    if tester_spec.parent_buildername is None:
      return bot_spec.BotMirror.create(
          buildername=tester_id.builder, mastername=tester_id.master)

    return bot_spec.BotMirror.create(
        mastername=tester_spec.parent_mastername or tester_id.master,
        buildername=tester_spec.parent_buildername,
        tester=tester_id.builder,
        tester_mastername=tester_id.master)

  def _calculate_repo_dir(self, solution_name):
    """Returns the relative path of the solution checkout to the root one."""
    if solution_name == 'src':
      return ''
    else:
      root_solution_name = 'src/'
      assert solution_name.startswith(root_solution_name)
      return solution_name[len(root_solution_name):]

  def files_changed_by_revision(self, revision, solution_name='src'):
    """Returns the files changed by the given revision.

    Args:
      revision (str): the git hash of a commit.
      solution_name (str): the gclient solution name, eg:
          "src" for chromium, "src/third_party/pdfium" for pdfium.
    """
    solution_name = solution_name.replace('\\', '/')
    repo_dir = self._calculate_repo_dir(solution_name)
    cwd = self.m.path['checkout'].join(repo_dir)

    with self.m.context(cwd=cwd):
      step_result = self.m.git(
          'diff', revision + '~1', revision, '--name-only',
          name='git diff to analyze commit',
          stdout=self.m.raw_io.output_text(),
          step_test_data=lambda:
              self.m.raw_io.test_api.stream_output('foo.cc'))

    paths = step_result.stdout.split()
    if repo_dir:
      paths = [self.m.path.join(repo_dir, path) for path in paths]
    if self.m.platform.is_win:
      # Looks like "analyze" wants POSIX slashes even on Windows (since git
      # uses that format even on Windows).
      paths = [path.replace('\\', '/') for path in paths]

    step_result.presentation.logs['files'] = paths
    return paths

  def revisions_between(
      self, start_revision, end_revision, solution_name='src'):
    """Returns the git commit hashes between the given range.

    Args:
      start_revision (str): the git hash of a parent commit.
      end_revision (str): the git hash of a child commit.
      solution_name (str): the gclient solution name, eg:
          "src" for chromium, "src/third_party/pdfium" for pdfium.

    Returns:
      A list of git commit hashes between `start_revision` (excluded) and
      `end_revision` (included), ordered from older commits to newer commits.
    """
    solution_name = solution_name.replace('\\', '/')
    repo_dir = self._calculate_repo_dir(solution_name)
    cwd = self.m.path['checkout'].join(repo_dir)

    with self.m.context(cwd=cwd):
      step_result = self.m.git('log', '--format=%H',
                               '%s..%s' % (start_revision, end_revision),
                               name='git commits in range',
                               stdout=self.m.raw_io.output_text(),
                               step_test_data=lambda:
                                   self.m.raw_io.test_api.stream_output('r1'))

    revisions = step_result.stdout.split()
    revisions.reverse()

    step_result.presentation.logs['revisions'] = revisions
    return revisions

  def existing_targets(self, targets, builder_id):
    """Returns a sublist of the given targets that exist in the build graph.

    We test whether a target exists or not by ninja.

    A "target" here is actually a node in ninja's build graph. For example:
      1. An executable target like browser_tests
      2. An object file like obj/path/to/Source.o
      3. An action like build/linux:gio_loader
      4. An generated header file like gen/library_loaders/libgio.h
      5. and so on

    Args:
     targets (list): A list of targets to be tested for existence.
     builder_id (BuilderId): The ID of the builder to run MB for.
    """
    # Run mb to generate or update ninja build files.
    if self.m.chromium.c.project_generator.tool == 'mb':
      self.m.chromium.mb_gen(builder_id, name='generate_build_files')

    # Run ninja to check existences of targets.
    args = ['--target-build-dir', self.m.chromium.output_dir]
    args.extend(['--ninja-path', self.m.depot_tools.ninja_path])
    for target in targets:
      args.extend(['--target', target])
    args.extend(['--json-output', self.m.json.output()])
    step = self.m.python(
        'check_targets', self.resource('check_target_existence.py'), args=args)
    return step.json.output['found']

  def compile_and_test_at_revision(self,
                                   bot_mirror,
                                   revision,
                                   requested_tests,
                                   use_analyze,
                                   test_repeat_count=None,
                                   skip_tests=False):
    """Compile the targets needed to execute the specified tests and run them.

    Args:
      bot_mirror (BotMirror): The BotMirror object describing the builder and
                              possibly tester to derive configuration from.
      revision (str): A string representing the commit hash of the revision to
                      test.
      requested_tests (dict):
          maps the test name (step name) to the names of the subtest to run.
          i.e. for GTests these are built into a test filter string, and passed
          in the command line. E.g.
              {'browser_tests': ['suite.test1', 'suite.test2']}
      use_analyze (bool):
          Whether to trim the list of tests to perform based on which files
          are actually affected by the revision.
      test_repeat_count (int or None):
          Repeat count to pass to the test. Note that we don't call the test
          this many times, we call the test once but pass this repeat factor as
          a parameter, and it's up to the test implementation to perform the
          repeats. Either 1 or None imply that no special flag for repeat will
          be passed.
      skip_tests (bool):
          If True, do not actually run the tests. Useful when we only want to
          isolate the targets for running elsewhere.

    Returns:
      A Tuple of
        - Test result dictionary of the form:
          {
            'failed test name':
              {
                'status': TestResult status,
                'valid': bool
              }
          }
        - dictionary of failed tests of the form:
          {
            'test name': list of tests
          }
        - RawResult object with compile step status and failure message
    """

    results = {}
    abbreviated_revision = revision[:7]
    with self.m.step.nest('test %s' % str(abbreviated_revision)):
      # Checkout code at the given revision to recompile.
      # TODO(stgao): refactor this out.
      bot_config = self.m.chromium_tests.create_bot_config_object([bot_mirror])
      bot_update_step, build_config = self.m.chromium_tests.prepare_checkout(
          bot_config, root_solution_revision=revision)

      # Figure out which test steps to run.
      requested_tests_to_run = [
          test for test in build_config.all_tests()
          if test.canonical_name in requested_tests
      ]

      # Figure out the test targets to be compiled.
      requested_test_targets = []
      for test in requested_tests_to_run:
        requested_test_targets.extend(test.compile_targets())
      requested_test_targets = sorted(set(requested_test_targets))

      actual_tests_to_run = requested_tests_to_run
      actual_compile_targets = requested_test_targets
      # Use dependency "analyze" to reduce tests to be run.
      if use_analyze:
        changed_files = self.files_changed_by_revision(revision)

        affected_test_targets, actual_compile_targets = (
            self.m.filter.analyze(
                changed_files,
                test_targets=requested_test_targets,
                additional_compile_targets=[],
                config_file_name='trybot_analyze_config.json',
                builder_id=bot_mirror.builder_id,
                additional_names=None))

        actual_tests_to_run = []
        for test in requested_tests_to_run:
          targets = test.compile_targets()
          if not targets:
            # No compile is needed for the test. Eg: checkperms.
            actual_tests_to_run.append(test)
            continue

          # Check if the test is affected by the given revision.
          for target in targets:
            if target in affected_test_targets:
              actual_tests_to_run.append(test)
              break

      if actual_compile_targets:
        raw_result = self.m.chromium_tests.compile_specific_targets(
            bot_config,
            bot_update_step,
            build_config,
            actual_compile_targets,
            tests_including_triggered=actual_tests_to_run,
            builder_id=bot_mirror.builder_id,
            override_bot_type='builder_tester')

        if raw_result.status != common_pb.SUCCESS:
          return None, None, raw_result
      for test in actual_tests_to_run:
        try:
          test.test_options = steps.TestOptions(
              test_filter=requested_tests.get(test.canonical_name),
              repeat_count=test_repeat_count,
              retry_limit=0 if test_repeat_count else None,
              run_disabled=bool(test_repeat_count))
        except NotImplementedError:
          # ScriptTests do not support test_options property
          pass

      # Run the tests.
      with self.m.chromium_tests.wrap_chromium_tests(bot_config,
                                                     actual_tests_to_run):
        if skip_tests:
          # Not actually running any tests.
          return {
              x: {
                  'status': self.TestResult.SKIPPED,
                  'valid': True
              } for x in requested_tests.keys()
          }, defaultdict(list), None

        _, failed_tests = self.m.test_utils.run_tests(
            self.m.chromium_tests.m,
            actual_tests_to_run,
            suffix=abbreviated_revision)

      # Process failed tests.
      failed_tests_dict = defaultdict(list)
      for failed_test in failed_tests:
        valid = failed_test.has_valid_results(suffix=abbreviated_revision)
        results[failed_test.name] = {
            'status': self.TestResult.FAILED,
            'valid': valid,
        }
        if valid:
          test_list = list(
              failed_test.failures(suffix=abbreviated_revision))
          results[failed_test.name]['failures'] = test_list
          failed_tests_dict[failed_test.name].extend(test_list)

      # Process passed tests.
      for test in actual_tests_to_run:
        if test not in failed_tests:
          results[test.name] = {
              'status': self.TestResult.PASSED,
              'valid': True,
          }

        if hasattr(test, 'pass_fail_counts'):
          pass_fail_counts = test.pass_fail_counts(suffix=abbreviated_revision)
          results[test.name]['pass_fail_counts'] = pass_fail_counts

        results[test.name]['step_metadata'] = test.step_metadata(
            suffix=abbreviated_revision)

      # Process skipped tests in two scenarios:
      # 1. Skipped by "analyze": tests are not affected by the given revision.
      # 2. Skipped because the requested tests don't exist at the given
      #    revision.
      for test_name in requested_tests.keys():
        if test_name not in results:
          results[test_name] = {
              'status': self.TestResult.SKIPPED,
              'valid': True,
          }

      return results, failed_tests_dict, None

  def configure_and_sync(self, target_tester_id, revision, builders=None):
    """Applies compile/test configs & syncs code.

    These are common tasks done in preparation ahead of building and testing
    chromium revisions, extracted as code share between the test and flake
    recipes.

    Args:
      target_tester_id (BuilderId): The ID of the tester to derive the
                                    configuration from.
      revision (str): A string representing the commit hash of the revision to
                      test.
      builders (BotDatabase): The database of builders.
    Returns: (bot_mirror, checked_out_revision, cached_revision)
    """
    # Figure out which builder configuration we should match for compile config.
    # Sometimes, the builder itself runs the tests and there is no tester. In
    # such cases, just treat the builder as a "tester". Thus, we default to
    # the target tester.
    builders = builders or self.m.chromium_tests.builders
    bot_mirror = self.get_bot_mirror_for_tester(
        target_tester_id, builders=builders)

    # Configure to match the compile config on the builder.
    bot_config = self.m.chromium_tests.create_bot_config_object(
        [bot_mirror.builder_id], builders=builders)
    self.m.chromium_tests.configure_build(
        bot_config, override_bot_type='builder_tester')

    # We rely on goma for fast compile. It's better to fail early if goma can't
    # start.
    self.m.chromium.apply_config('goma_failfast')

    # Configure to match the test config on the tester, as builders don't have
    # the settings for swarming tests.
    if bot_mirror.tester_id:
      tester_spec = builders[bot_mirror.tester_id]
      for key, value in tester_spec.swarming_dimensions.iteritems():
        self.m.chromium_swarming.set_default_dimension(key, value)

    # Record the current revision of the checkout and HEAD of the git cache.
    checked_out_revision, cached_revision = self.record_previous_revision(
        bot_config)

    # Sync code.
    self.m.chromium_tests.prepare_checkout(
        bot_config, root_solution_revision=revision)

    # TODO(stgao): Fix the issue that precommit=False adds the tag 'purpose:CI'.
    self.m.chromium_swarming.configure_swarming('chromium', precommit=False)

    self.m.step.active_result.presentation.properties['target_buildername'] = (
        bot_mirror.builder_id.builder)

    return bot_mirror, checked_out_revision, cached_revision

  def record_previous_revision(self, bot_config):
    """Records the latest checked out and cached revisions.

    Examines the checkout and records the latest available revision for the
    first gclient solution.

    This also records the latest revision available in the local git cache.

    Returns:
      A pair of revisions (checked_out_revision, cached_revision), or None, None
      if the checkout directory does not exist.
    """
    src_root = self.m.gclient.c.src_root
    first_solution = (
        self.m.gclient.c.solutions[0].name
        if self.m.gclient.c.solutions else None)

    src_root = src_root or first_solution
    if not src_root:  # pragma: no cover.
      # We don't know where to look for the revisions
      return None, None

    # self.m.path['checkout'] is not set yet, so we get it from
    # chromium_checkout.
    checkout_dir = self.m.chromium_checkout.get_checkout_dir(bot_config)
    full_checkout_path = checkout_dir.join(src_root)
    if not self.m.path.exists(full_checkout_path):
      return None, None
    with self.m.context(cwd=full_checkout_path):
      checked_out_revision = None
      try:
        previously_checked_out_revision_step = self.m.git(
            'rev-parse',
            'HEAD',
            stdout=self.m.raw_io.output(),
            name='record previously checked-out revision',
            step_test_data=
            lambda: self.m.raw_io.test_api.stream_output(_GIT_REV_PARSE_OUTPUT))

        # Sample output:
        # `d4316eba6ba2b9e88eba8d805babcdfdbbc6e74a`
        matches = re.match(
            '(?P<revision>[a-fA-f0-9]{40})',
             previously_checked_out_revision_step.stdout.strip())
        if matches:
          checked_out_revision = matches.group('revision')
          previously_checked_out_revision_step.presentation.properties[
              'previously_checked_out_revision'] = checked_out_revision
      except (self.m.step.StepFailure, OSError):
        # This is expected if the directory or the git repo do not exist.
        pass

      cached_revision = None
      try:
        previously_cached_revision_step = self.m.git(
            'ls-remote',
            'origin',
            'refs/heads/master',
            stdout=self.m.raw_io.output(),
            name='record previously cached revision',
            step_test_data=
            lambda: self.m.raw_io.test_api.stream_output(_GIT_LS_REMOTE_OUTPUT))

        # Sample output:
        # `d4316eba6ba2b9e88eba8d805babcdfdbbc6e74a  refs/heads/master`
        matches = re.match('(?P<revision>[a-fA-f0-9]{40})\s*\S*',
                           previously_cached_revision_step.stdout.strip())
        if matches:
          cached_revision = matches.group('revision')
          previously_cached_revision_step.presentation.properties[
          'previously_cached_revision'] = cached_revision
      except (self.m.step.StepFailure, OSError):
        # This is expected if the directory or the git repo do not exist.
        pass
      return checked_out_revision, cached_revision
