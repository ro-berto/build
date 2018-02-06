# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from collections import defaultdict
import json
import re

from recipe_engine import recipe_api


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

    previous_revision = '%s~1' % revision
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

  def existing_targets(self, targets, mb_mastername, mb_buildername):
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
     mb_mastername (str): The mastername to run MB with.
     mb_buildername (str): The buildername to run MB with.
    """
    # Run mb to generate or update ninja build files.
    if self.m.chromium.c.project_generator.tool == 'mb':
      self.m.chromium.run_mb(mb_mastername, mb_buildername,
                             name='generate_build_files')

    # Run ninja to check existences of targets.
    args = ['--target-build-dir', self.m.chromium.output_dir]
    args.extend(['--ninja-path', self.m.depot_tools.ninja_path])
    for target in targets:
      args.extend(['--target', target])
    args.extend(['--json-output', self.m.json.output()])
    step = self.m.python(
        'check_targets', self.resource('check_target_existence.py'), args=args)
    return step.json.output['found']

  def compile_and_test_at_revision(self, api, target_mastername,
                                   target_buildername, target_testername,
                                   revision, requested_tests, use_analyze,
                                   test_repeat_count=None, skip_tests=False):
    """Compile the targets needed to execute the specified tests and run them.

    Args:
      api (RecipeApi): With the dependencies injected by the calling recipe.
      target_mastername (str): Which master to derive the configuration off of.
      target_buildername (str): likewise
      target_testername (str): likewise
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
    """

    results = {}
    debug_info = {}
    abbreviated_revision = revision[:7]
    with api.m.step.nest('test %s' % str(abbreviated_revision)):
      # Checkout code at the given revision to recompile.
      bot_id = {
          'mastername': target_mastername,
          'buildername': target_buildername,
          'tester': target_testername}
      debug_info['bot_id'] = bot_id
      bot_config = api.m.chromium_tests.create_generalized_bot_config_object(
          [bot_id])
      bot_update_step, bot_db = api.m.chromium_tests.prepare_checkout(
          bot_config, root_solution_revision=revision)

      # Figure out which test steps to run.
      all_tests, _ = api.m.chromium_tests.get_tests(bot_config, bot_db)

      # Makes sure there are no steps with the same step name.
      requested_tests_to_run_dict = {}
      tests_metadata = defaultdict(list)
      for test in all_tests:
        if test.name in requested_tests:
          if not requested_tests_to_run_dict.get(test.name):
            requested_tests_to_run_dict[test.name] = test
          tests_metadata[test.name].append(test.step_metadata(api))
      debug_info['actual_tests_to_run'] = tests_metadata
      requested_tests_to_run = requested_tests_to_run_dict.values()

      api.python.succeeding_step(
        'debug_get_requested_tests_to_run', [json.dumps(debug_info, indent=2)],
        as_log='debug_get_requested_tests_to_run')

      # Figure out the test targets to be compiled.
      requested_test_targets = []
      for test in requested_tests_to_run:
        requested_test_targets.extend(test.compile_targets(api))
      requested_test_targets = sorted(set(requested_test_targets))

      actual_tests_to_run = requested_tests_to_run
      actual_compile_targets = requested_test_targets
      # Use dependency "analyze" to reduce tests to be run.
      if use_analyze:
        changed_files = self.files_changed_by_revision(revision)

        affected_test_targets, actual_compile_targets = (
            api.m.filter.analyze(
                changed_files,
                test_targets=requested_test_targets,
                additional_compile_targets=[],
                config_file_name='trybot_analyze_config.json',
                mb_mastername=target_mastername,
                mb_buildername=target_buildername,
                additional_names=None))

        actual_tests_to_run = []
        for test in requested_tests_to_run:
          targets = test.compile_targets(api)
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
        api.m.chromium_tests.compile_specific_targets(
            bot_config,
            bot_update_step,
            bot_db,
            actual_compile_targets,
            tests_including_triggered=actual_tests_to_run,
            mb_mastername=target_mastername,
            mb_buildername=target_buildername,
            override_bot_type='builder_tester')

      for test in actual_tests_to_run:
        try:
          test.test_options = api.m.chromium_tests.steps.TestOptions(
              test_filter=requested_tests.get(test.name),
              repeat_count=test_repeat_count,
              retry_limit=0 if test_repeat_count else None,
              run_disabled=bool(test_repeat_count))
        except NotImplementedError:
          # ScriptTests do not support test_options property
          pass

      # Run the tests.
      with api.m.chromium_tests.wrap_chromium_tests(
          bot_config, actual_tests_to_run):
        if skip_tests:
          # Not actually running any tests.
          return {
              x: {
                  'status': self.TestResult.SKIPPED,
                  'valid': True
              } for x in requested_tests.keys()
          }, defaultdict(list)

        failed_tests = api.m.test_utils.run_tests(
            api.chromium_tests.m, actual_tests_to_run,
            suffix=abbreviated_revision)

      # Process failed tests.
      failed_tests_dict = defaultdict(list)
      for failed_test in failed_tests:
        valid = failed_test.has_valid_results(api, suffix=abbreviated_revision)
        results[failed_test.name] = {
            'status': self.TestResult.FAILED,
            'valid': valid,
        }
        if valid:
          test_list = list(
              failed_test.failures(api, suffix=abbreviated_revision))
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
            api, suffix=abbreviated_revision)

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

      return results, failed_tests_dict

  def configure_and_sync(self, api, tests, buildbucket, target_mastername,
                         target_testername, revision):
    """Loads tests from buildbucket, applies bot/swarming configs & syncs code.

    These are common tasks done in preparation ahead of building and testing
    chromium revisions, extracted as code share between the test and flake
    recipes.

    Args:
      api (RecipeApi): With the dependencies injected by the calling recipe.
      tests (dict):
          maps the test name (step name) to the names of the subtest to run.
          i.e. for GTests these are built into a test filter string, and passed
          in the command line. E.g.
              {'browser_tests': ['suite.test1', 'suite.test2']}
          These are likely superseded by the contents of buildbucket below.
      buildbucket (str or dict):
          JSON string or dict containing a buildbucket job spec from which to
          extract the tests to execute. Parsed if the `tests` parameter above is
          not provided.
      target_mastername (str): Which master to derive the configuration off of.
      target_testername (str): likewise
      revision (str): A string representing the commit hash of the revision to
                      test.
    Returns: (tests, target_buildername)
    """

    if not tests:
      # tests should be saved in build parameter in this case.

      # If the recipe is run by swarmbucket, the property 'buildbucket' will be
      # a dict instead of a string containing json.
      if isinstance(buildbucket, dict):
        buildbucket_json = buildbucket
      else:
        buildbucket_json = json.loads(buildbucket)
      build_id = buildbucket_json['build']['id']
      get_build_result = api.buildbucket.get_build(build_id)
      tests = json.loads(
          get_build_result.stdout['build']['parameters_json']).get(
              'additional_build_parameters', {}).get('tests')

    assert tests, 'No failed tests were specified.'

    # Figure out which builder configuration we should match for compile config.
    # Sometimes, the builder itself runs the tests and there is no tester. In
    # such cases, just treat the builder as a "tester". Thus, we default to
    # the target tester.
    tester_config = api.chromium_tests.builders.get(
        target_mastername).get('builders', {}).get(target_testername)
    target_buildername = (tester_config.get('parent_buildername') or
                          target_testername)

    # Configure to match the compile config on the builder.
    bot_config = api.chromium_tests.create_bot_config_object(
        target_mastername, target_buildername)
    api.chromium_tests.configure_build(
        bot_config, override_bot_type='builder_tester')

    api.chromium.apply_config('goma_failfast')

    (checked_out_revision, cached_revision) = self.record_previous_revision(
        api, bot_config)
    # Configure to match the test config on the tester, as builders don't have
    # the settings for swarming tests.
    if target_buildername != target_testername:
      for key, value in tester_config.get('swarming_dimensions', {}
                                          ).iteritems():
        api.swarming.set_default_dimension(key, value)
    # TODO(stgao): Fix the issue that precommit=False adds the tag 'purpose:CI'.
    api.chromium_swarming.configure_swarming('chromium', precommit=False)

    # Sync to revision,
    api.chromium_tests.prepare_checkout(
        bot_config,
        root_solution_revision=revision)

    return tests, target_buildername, checked_out_revision, cached_revision

  def record_previous_revision(self, api, bot_config):
    """Records the latest checked out and cached revisions.

    Examines the checkout and records the latest available revision for the
    first gclient solution.

    This also records the latest revision available in the local git cache.

    Args:
      api (RecipeApi): With the dependencies injected by the calling recipe
    Returns:
      A pair of revisions (checked_out_revision, cached_revision), or None, None
      if the checkout directory does not exist.
    """
    src_root = api.gclient.c.src_root
    first_solution = (api.gclient.c.solutions[0].name
                      if api.gclient.c.solutions else None)

    src_root = src_root or first_solution
    if not src_root:  # pragma: no cover.
      # We don't know where to look for the revisions
      return None, None

    # api.path['checkout'] is not set yet, so we get it from chromium_checkout.
    checkout_dir = api.chromium_checkout.get_checkout_dir(bot_config)
    full_checkout_path = checkout_dir.join(src_root)
    if not api.path.exists(full_checkout_path):
      return None, None
    with api.context(cwd=full_checkout_path):
      checked_out_revision = None
      try:
        previously_checked_out_revision_step = api.git(
            'rev-parse', 'HEAD',
            stdout=api.raw_io.output(),
            name='record previously checked-out revision',
            step_test_data=lambda: api.raw_io.test_api.stream_output(
                _GIT_REV_PARSE_OUTPUT))

        # Sample output:
        # `d4316eba6ba2b9e88eba8d805babcdfdbbc6e74a`
        matches = re.match(
            '(?P<revision>[a-fA-f0-9]{40})',
             previously_checked_out_revision_step.stdout.strip())
        if matches:
          checked_out_revision = matches.group('revision')
          previously_checked_out_revision_step.presentation.properties[
              'previously_checked_out_revision'] = checked_out_revision
      except (api.step.StepFailure, OSError):
        # This is expected if the directory or the git repo do not exist.
        pass

      cached_revision = None
      try:
        previously_cached_revision_step = api.git(
            'ls-remote', 'origin', 'refs/heads/master',
            stdout=api.raw_io.output(),
            name='record previously cached revision',
            step_test_data=lambda: api.raw_io.test_api.stream_output(
                _GIT_LS_REMOTE_OUTPUT))

        # Sample output:
        # `d4316eba6ba2b9e88eba8d805babcdfdbbc6e74a  refs/heads/master`
        matches = re.match('(?P<revision>[a-fA-f0-9]{40})\s*\S*',
                           previously_cached_revision_step.stdout.strip())
        if matches:
          cached_revision = matches.group('revision')
          previously_cached_revision_step.presentation.properties[
          'previously_cached_revision'] = cached_revision
      except (api.step.StepFailure, OSError):
        # This is expected if the directory or the git repo do not exist.
        pass
      return checked_out_revision, cached_revision
