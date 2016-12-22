# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from collections import defaultdict

from recipe_engine import recipe_api


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
    step_result = self.m.git('diff', revision + '~1', revision, '--name-only',
                             name='git diff to analyze commit',
                             stdout=self.m.raw_io.output(),
                             cwd=cwd,
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

    step_result = self.m.git('log', '--format=%H',
                             '%s..%s' % (start_revision, end_revision),
                             name='git commits in range',
                             stdout=self.m.raw_io.output(),
                             cwd=cwd,
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
    for target in targets:
      args.extend(['--target', target])
    args.extend(['--json-output', self.m.json.output()])
    step = self.m.python(
        'check_targets', self.resource('check_target_existence.py'), args=args)
    return step.json.output['found']

  def compile_and_test_at_revision(self, api, target_mastername,
                                   target_buildername, target_testername,
                                   revision, requested_tests, use_analyze):
    """Compile the targets needed to execute the specified tests and run them.

    Args:
      api (RecipeApi): With the dependencies injected by the calling recipe.
      target_mastername (str): Which master to derive the configuration off of.
      target_buildername (str): likewise
      target_tester_name (str): likewise
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
      """
    results = {}
    with api.m.step.nest('test %s' % str(revision)):
      # Checkout code at the given revision to recompile.
      bot_id = {
          'mastername': target_mastername,
          'buildername': target_buildername,
          'tester': target_testername}
      bot_config = api.m.chromium_tests.create_generalized_bot_config_object(
          [bot_id])
      bot_update_step, bot_db = api.m.chromium_tests.prepare_checkout(
          bot_config, root_solution_revision=revision)

      # Figure out which test steps to run.
      all_tests, _ = api.m.chromium_tests.get_tests(bot_config, bot_db)
      requested_tests_to_run = [
          test for test in all_tests if test.name in requested_tests]

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
              test_filter=requested_tests.get(test.name))
        except NotImplementedError:
          # ScriptTests do not support test_options property

          # TODO(robertocn): Figure out how to handle ScriptTests without hiding
          # ths error.
          pass
      # Run the tests.
      with api.m.chromium_tests.wrap_chromium_tests(
          bot_config, actual_tests_to_run):
        failed_tests = api.m.test_utils.run_tests(
            api, actual_tests_to_run, suffix=str(revision))

      # Process failed tests.
      failed_tests_dict = defaultdict(list)
      for failed_test in failed_tests:
        valid = failed_test.has_valid_results(api, suffix=revision)
        results[failed_test.name] = {
            'status': self.TestResult.FAILED,
            'valid': valid,
        }
        if valid:
          test_list = list(failed_test.failures(api, suffix=revision))
          results[failed_test.name]['failures'] = test_list
          failed_tests_dict[failed_test.name].extend(test_list)

      # Process passed tests.
      for test in actual_tests_to_run:
        if test not in failed_tests:
          results[test.name] = {
              'status': self.TestResult.PASSED,
              'valid': True,
          }

      # TODO(robertocn): Remove this once flake.py lands. For now, it's required
      # to provide coverage for the .pass_fail_coutns code.
      for test in actual_tests_to_run:
        if hasattr(test, 'pass_fail_counts'):
          pass_fail_counts = test.pass_fail_counts(suffix=revision)
          results[test.name]['pass_fail_counts'] = pass_fail_counts

      # Process skipped tests in two scenarios:
      # 1. Skipped by "analyze": tests are not affected by the given revision.
      # 2. Skipped because the requested tests don't exist at the given revision.
      for test_name in requested_tests.keys():
        if test_name not in results:
          results[test_name] = {
              'status': self.TestResult.SKIPPED,
              'valid': True,
          }

      return results, failed_tests_dict
