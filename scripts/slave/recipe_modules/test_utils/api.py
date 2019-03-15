# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import itertools
import json

from recipe_engine import recipe_api
from recipe_engine import util as recipe_util

from . import canonical
from .util import GTestResults, TestResults

from RECIPE_MODULES.recipe_engine.json.api import JsonOutputPlaceholder


class TestResultsOutputPlaceholder(JsonOutputPlaceholder):
  def result(self, presentation, test):
    ret = super(TestResultsOutputPlaceholder, self).result(presentation, test)
    return TestResults(ret)


class GTestResultsOutputPlaceholder(JsonOutputPlaceholder):
  def result(self, presentation, test):
    ret = super(GTestResultsOutputPlaceholder, self).result(presentation, test)
    return GTestResults(ret)

class TestUtilsApi(recipe_api.RecipeApi):
  """This class helps run tests and parse results.

  Tests are run in [up to] three stages:
    * 'with patch'
    * 'without patch'
    * 'retry with patch'

  The first stage applies the patch and runs the tests. If this passes, we're
  finished. Assuming that tests fail or return invalid results, then we deapply
  the patch and try running the tests again. If the failures are the same, then
  this is an issue with tip of tree and we ignore the failures.

  Finally, we roll the checkout and reapply the patch, and then rerun the
  failing tests. This helps confirm whether the failures were flakes or
  deterministic errors.
  """

  # Some test runners (such as run_web_tests.py and python tests) returns the
  # number of failures as the return code. They need to cap the return code at
  # 101 to avoid overflow or colliding with reserved values from the shell.
  MAX_FAILURES_EXIT_STATUS = 101

  # This magic string is depended on by other infra tools.
  INVALID_RESULTS_MAGIC = 'TEST RESULTS WERE INVALID'

  def __init__(self, max_reported_failures, *args, **kwargs):
    super(TestUtilsApi, self).__init__(*args, **kwargs)
    self._max_reported_failures = int(max_reported_failures)

  @property
  def canonical(self):
    return canonical

  def limit_failures(self, failures, limit=None):
    """Limit failures of a step to prevent large results JSON.

    Args:
      failures - An iterable containing the failures that resulted from some
                 step.
      limit - The maxmium number of failures to display in the results.
    Returns:
      A tuple containing 2 elements:
        1. The list of the subset of at most *limit* elements of *failures*,
           suitable for iterating over and indexing into structures that are
           indexed by the failure names.
        2. The list of failures suitable for including in the step's text. If
           *failures* contains more elements than *limit*, it will contain an
           element indicating the number of additional failures.
    """
    if limit is None:
      limit = self._max_reported_failures
    if len(failures) <= limit:
      return failures, failures
    overflow_line = '... %d more (%d total) ...' % (
        len(failures) - limit, len(failures))
    # failures might be a set, which doesn't support slicing, so create a list
    # out of an islice so that only the elemnts we are keeping are copied
    limited_failures = list(itertools.islice(failures, limit))
    return limited_failures, limited_failures + [overflow_line]

  @staticmethod
  def format_step_text(data):
    """
    Returns string suitable for use in a followup function's step result's
    presentation step text.

    Args:
      data - iterable of sections, where each section is one of:
        a) tuple/list with one element for a single-line section
           (always displayed)
        b) tuple/list with two elements where first one is the header,
           and the second one is an iterable of content lines; if there are
           no contents, the whole section is not displayed
    """
    step_text = []
    for section in data:
      if len(section) == 1:
        # Make it possible to display single-line sections.
        step_text.append('<br/>%s<br/>' % section[0])
      elif len(section) == 2:
        # Only displaying the section (even the header) when it's non-empty
        # simplifies caller code.
        if section[1]:
          step_text.append('<br/>%s<br/>' % section[0])
          step_text.extend(('%s<br/>' % line for line in section[1]))
      else:  # pragma: no cover
        raise ValueError(
            'Expected a one or two-element list, got %r instead.' % section)
    return ''.join(step_text)

  def present_gtest_failures(self, step_result, presentation=None):
    """Update a step result's presentation with details of gtest failures.

    If the provided step result contains valid gtest results, then the
    presentation will be updated to include information about the failing
    tests, including logs for the individual failures.

    The max_reported_failures property modifies this behavior by limiting the
    number of tests that will appear in the step text and have their logs
    included. If the limit is exceeded the step text will indicate the number
    of additional failures.

    Args:
      step_result - The step result that potentially contains gtest results.
      presentation - The presentation to update. If not provided or None, the
                     presentation of *step_result* will be updated.
    Returns:
      The gtest_results object if it is present in the step result, otherwise
      None.
    """
    r = getattr(step_result, 'test_utils', None)
    r = getattr(r, 'gtest_results', None)

    if r and r.valid:
      p = presentation or step_result.presentation

      def emit_log(f, prefix):
        # FIXME: We could theoretically split up each run more. This would
        # require some refactoring in util.py to store each individual run's
        # logs, which we don't do currently.
        log_name = '%s: %s (status %s)' % (
            prefix, f, ','.join(set(r.raw_results[f])))
        p.logs[log_name] = [
            "Test '%s' completed with the following status(es): '%s'" % (
                f, '\',\''.join(r.raw_results[f])),
            '\n',
            "Test '%s' had the following logs when run:\n" % f,
            '\n',
            '=' * 80 + '\n',
            '\n',
        ] + r.logs[f] + [
            '\n',
            '=' * 80,
        ]

      deterministic_failures_set = set(r.deterministic_failures)
      flaky_failures_set = set(r.unique_failures) - deterministic_failures_set

      deterministic_failures, deterministic_failures_text = (
          self.limit_failures(sorted(deterministic_failures_set)))
      flaky_failures, flaky_failures_text = (
          self.limit_failures(sorted(flaky_failures_set)))
      for f in deterministic_failures:
        emit_log(f, 'Deterministic failure')
      for f in flaky_failures:
        emit_log(f, 'Flaky failure')

      p.step_text += self.format_step_text([
          ['deterministic failures [caused step to fail]:',
           deterministic_failures_text],
          ['flaky failures [ignored]:', flaky_failures_text],
      ])
    return r

  def run_tests(self, caller_api, tests, suffix, sort_by_shard=False):
    """
    Utility function for running a list of tests and returning the failed tests.

    Args:
      caller_api - caller's recipe API; this is needed because self.m here
                   is different than in the caller (different recipe modules
                   get injected depending on caller's DEPS vs. this module's
                   DEPS)
                   This must include the 'swarming' recipe module, in order to
                   use the grouping logic in this method. Unfortunately we can't
                   import this module in the test_utils module, as it would
                   cause a circular dependency.
      tests - iterable of objects implementing the Test interface above
      suffix - custom suffix, e.g. "with patch", "without patch" indicating
               context of the test run
      sort_by_shard - sort the order of triggering depends on the number of
                      shards.
    Returns:
      A tuple of (list of tests with invalid results,
                  list of tests which failed)


    """
    if not hasattr(caller_api, 'chromium_swarming'):
      self.m.python.failing_step(
          'invalid caller_api',
          'caller_api must include the chromium_swarming recipe module')

    local_tests = []
    swarming_tests = []
    for test in tests:
      if isinstance(test, caller_api.chromium_tests.steps.SwarmingTest):
        swarming_tests.append(test)
      else:
        local_tests.append(test)

    if sort_by_shard:
      # Trigger tests which have a large number of shards earlier. They usually
      # take longer to complete, and triggering take a few minutes, so this
      # should get us a few extra minutes of speed.
      swarming_tests.sort(key=lambda t: -t.shards)

    groups = [LocalGroup(local_tests), SwarmingGroup(swarming_tests)]

    nest_name = 'test_pre_run (%s)' % suffix if suffix else 'test_pre_run'

    with self.m.step.nest(nest_name):
      for group in groups:
        group.pre_run(caller_api, suffix)

    for group in groups:
      group.run(caller_api, suffix)

    failed_tests = []
    invalid_results = []
    for test in tests:
      # Note that this is technically O(n^2). We expect n to be small.
      if not test.has_valid_results(caller_api, suffix):
        invalid_results.append(test)
      elif test.deterministic_failures(
          caller_api, suffix) and test not in failed_tests:
        failed_tests.append(test)

    return invalid_results, failed_tests

  def run_tests_with_patch(self, caller_api, tests, retry_failed_shards=False):
    """Run tests and returns failures.

    Args:
      caller_api: The api object given by the caller of this module.
      tests: A list of test suites to run with the patch.
      retry_failed_shards: If true, attempts to retry failed shards of swarming
                           tests.

    Returns: A tuple (invalid_test_suites, all_failing_test_suites).
      invalid_test_suites: Test suites that do not have valid test results.
      all_failing_test_suites:
          This includes test suites than ran but have failing tests, test suites
          that do not have valid test results, and test suites that failed with
          otherwise unspecified reasons. This is a superset of
          invalid_test_suites.
    """
    invalid_test_suites, all_failing_test_suites = self.run_tests(
        caller_api, tests, 'with patch', sort_by_shard=True)

    for t in invalid_test_suites:
      # No need to re-add a test_suite that is already in the list.
      if t not in all_failing_test_suites:
        all_failing_test_suites.append(t)

    if retry_failed_shards:
      # Assume that non swarming test retries probably won't help.
      swarming_test_suites = []
      for test_suite in all_failing_test_suites:
        if test_suite.runs_on_swarming:
          swarming_test_suites.append(test_suite)

      if swarming_test_suites:
        new_invalid, _ = self.run_tests(
            caller_api, swarming_test_suites, 'retry shards with patch',
            sort_by_shard=True)
        # If we have valid test results from one of the runs of a test suite,
        # then that test suite by definition doesn't have invalid test results.
        invalid_test_suites = list(set(invalid_test_suites).intersection(
            set(new_invalid)))

        # Some suites might be passing now, since we retried some tests. Remove
        # any suites which are now fully passing.
        # with_patch_failures_including_retry appropriately takes 'retry shards
        # with patch' and 'with patch' runs into account.
        for t in all_failing_test_suites:
          valid, failures = t.with_patch_failures_including_retry(caller_api)
          if valid and not failures:
            all_failing_test_suites.remove(t)

    # Set metadata about invalid test suites.
    for t in invalid_test_suites:
      self._invalid_test_results(t)

    return (invalid_test_suites, all_failing_test_suites)

  def _invalid_test_results(self, test):
    """Marks test results as invalid.

    If |fatal| is True, emits a failing step. Otherwise emits a succeeding step.
    """
    self.m.tryserver.set_invalid_test_results_tryjob_result()

    # Record a step with INVALID_RESULTS_MAGIC, which chromium_try_flakes uses
    # for analysis.
    self.m.python.succeeding_step(test.name, self.INVALID_RESULTS_MAGIC)

  def _summarize_new_and_ignored_failures(
      self, test, new_failures, ignored_failures, suffix, failure_text,
      ignored_text):
    """Summarizes new and ignored failures in the test_suite |test|.

    Args:
      test: A test suite that's been retried.
      new_failures: Failures that are potentially caused by the patched CL.
      ignored_failures: Failures that are not caused by the patched CL.
      suffix: Should be either 'retry with patch summary' or 'retry summary'.
      failure_text: A user-visible string describing new_failures.
      ignored_text: A user-visible string describing ignored_failures.

    Returns:
      A Boolean describing whether the retry succeeded. Which is to say, the
      patched CL did not cause the test suite to have deterministically failing
      tests.
    """
    # We add a failure_reason even if we don't mark the build as a failure. This
    # will contribute to the failure hash if the build eventually fails.
    self.m.tryserver.add_failure_reason({
      'test_name': test.name,
      'new_failures': sorted(new_failures),
    })

    # TODO(crbug.com/914213): Remove webkit_layout_tests reference.
    if test.name == 'webkit_layout_tests' or test.name == 'blink_web_tests':
      dest_file = '%s.json' % suffix.replace(' ', '_')
      self._archive_retry_summary({
          'failures': sorted(new_failures),
          'ignored': sorted(ignored_failures)
      }, dest_file)

    step_name = '%s (%s)' % (test.name, suffix)
    _, new_failures = self.limit_failures(new_failures)
    _, ignored_failures = self.limit_failures(ignored_failures)
    step_text = self.format_step_text([
        [failure_text, new_failures],
        [ignored_text, ignored_failures]
    ])

    result = self.m.python.succeeding_step(step_name, step_text)
    if new_failures:
      result.presentation.status = self.m.step.FAILURE
      self.m.tryserver.set_test_failure_tryjob_result()
    elif ignored_failures:
      result.presentation.status = self.m.step.WARNING

    return not bool(new_failures)


  def summarize_test_with_patch_deapplied(self, caller_api, test_suite):
    """Summarizes test results after a CL has been retried with patch deapplied.

    Args:
      If there are no new failures, this method will emit a passing step.
      If there are new failures, this method will emit a step whose presentation
      status is 'FAILURE'.

    Returns:
      A Boolean describing whether the retry succeeded. Which is to say, all
      tests that failed in the original run also failed in the retry, which
      suggests that the error is due to an issue with top of tree, and should
      not cause the CL to fail.
    """
    valid_results, ignored_failures = (
        test_suite.without_patch_failures_to_ignore(caller_api))
    if not valid_results:
      self._invalid_test_results(test_suite)

      # If there are invalid results from the deapply patch step, treat this as
      # if all tests passed which prevents us from ignoring any test failures
      # from 'with patch'.
      ignored_failures = set()

    valid_results, failures = test_suite.with_patch_failures_including_retry(
        caller_api)
    if valid_results:
      new_failures = failures - ignored_failures
    else:
      new_failures = set(['all initial tests failed'])

    failure_text = ('Failed with patch, succeeded without patch:')
    ignored_text = ('Tests ignored as they also fail without patch:')
    return self._summarize_new_and_ignored_failures(
        test_suite, new_failures, ignored_failures, 'retry summary',
        failure_text, ignored_text)

  def summarize_test_with_patch_reapplied(self, caller_api, test_suite):
    """Summarizes test results after a CL has been retried with patch reapplied.

    Returns:
      A Boolean describing whether the retry succeeded. Which is to say, whether
      there are tests that failed in 'with patch' and 'retry with patch', but
      not in 'without patch'.
    """
    valid_results, _, new_failures = test_suite.retry_with_patch_results(
        caller_api)

    # We currently do not attempt to recover from invalid test results on the
    # retry. Record a failing step with INVALID_RESULTS_MAGIC, which
    # chromium_try_flakes uses for analysis.
    if not valid_results:
      self._invalid_test_results(test_suite)
      return False

    # Assuming both 'with patch' and 'retry with patch' produced valid results,
    # look for the intersection of failures.
    valid_results, initial_failures = (
        test_suite.with_patch_failures_including_retry(caller_api))
    if valid_results:
      repeated_failures = new_failures & initial_failures
    else:
      repeated_failures = new_failures

    # Assuming 'without patch' produced valid results, subtract those from
    # repeated failures, as they're likely problems with tip of tree.
    valid_results, without_patch_failures = (
        test_suite.without_patch_failures_to_ignore(caller_api))
    if valid_results:
      new_failures = repeated_failures - without_patch_failures
      ignored_failures = without_patch_failures
    else:
      new_failures = repeated_failures
      ignored_failures = set()

    failure_text = ('Failed with patch twice, succeeded without patch:')
    ignored_text = ('Tests ignored as they succeeded on retry:')
    return self._summarize_new_and_ignored_failures(
        test_suite, new_failures, ignored_failures, 'retry with patch summary',
        failure_text=failure_text, ignored_text=ignored_text)

  def summarize_failing_test_with_no_retries(self, caller_api, test_suite):
    """Summarizes a failing test suite that is not going to be retried."""
    valid_results, new_failures = (
        test_suite.with_patch_failures_including_retry(caller_api))

    if not valid_results: # pragma: nocover
      self.m.python.infra_failing_step(
          '{} assertion'.format(test_suite.name),
          'This line should never be reached. If a test has invalid results '
          'and is not going to be retried, then a failing step should have '
          'already been emitted.')

    failure_text = ('Tests failed, not being retried')
    ignored_text = ('Tests ignored')
    return self._summarize_new_and_ignored_failures(
        test_suite, new_failures, set(), 'with patch summary',
        failure_text=failure_text, ignored_text=ignored_text)

  def _findit_potential_test_flakes(self, caller_api, test_suite):
    """Returns test failures that FindIt views as potential flakes.

    This method returns tests that:
      * Failed in 'with patch' or 'retry shards with patch', but not because of
        UNKNOWN/NOTRUN
      * Succeeded in 'without patch'

    Test failures in 'retry shards with patch' can be considered as valid
    flakes, even if 'with patch' has no valid results'.

    Returns:
      findit_potential_flakes: A set of test names that should be considered
                               candidates as flaky tests.
    """
    valid_results = test_suite.has_valid_results(caller_api, 'with patch')
    valid_retry_shards_results = test_suite.has_valid_results(
        caller_api, 'retry shards with patch')
    if not (valid_results or valid_retry_shards_results):
      return set()

    suffix = 'with patch' if valid_results else 'retry shards with patch'
    with_patch_failures = set(test_suite.deterministic_failures(
        caller_api, suffix))

    # FindIt wants to ignore failures that have status UNKNOWN/NOTRUN. This
    # logic will eventually live in FindIt, but for now, is implemented here.
    not_run = test_suite.findit_notrun(caller_api, suffix)
    with_patch_failures = with_patch_failures - not_run

    # To reduce false positives, FindIt only wants tests to be marked as
    # potentially flaky if the the test passed in 'without patch'.
    valid_results, ignored_failures = (
        test_suite.without_patch_failures_to_ignore(caller_api))
    # If we've retried a shard, and we didn't run 'without patch', then the
    # tests passed the second time, and there wasn't a need to run the tests
    # without the patch. Only give up if 'without patch' never runs.
    if not (valid_results or valid_retry_shards_results):
      return set()

    return with_patch_failures - (ignored_failures or set())

  def summarize_findit_flakiness(self, caller_api, test_suites):
    """Exports a summary of flakiness for post-processing by FindIt.

    There are several types of test flakiness. FindIt categories these by the
    layer at which the flakiness is discovered. One of these categories is for a
    test that fails, but when retried in a separate step, succeeds. This
    currently applies to 'retry with patch', but will also apply to shard-layer
    retries when those are introduced. These are labeled 'Step Layer Flakiness'.

    FindIt also wants to know about 'with patch' tests that caused the build to
    fail. If a future build with the same CL succeeds, then the tests are
    potential flakes. Although it's also possible that rolling tip of tree
    caused the results to change. These are labeled
    'Failing With Patch Tests That Caused Build Failure'.

    This function emits a step with a fixed name, and metadata for FindIt.
    Before making changes to this function, check with the FindIt team to ensure
    that their post-processing will still work correctly.
    """
    step_layer_flakiness = {}
    for test_suite in test_suites:
      potential_test_flakes = self._findit_potential_test_flakes(caller_api,
                                                                 test_suite)

      # We only want to consider tests that failed in 'with patch' but succeeded
      # when retried, either by 'retry shards with patch' or 'retry with patch'.
      # If a test didn't run in either of these steps, then we ignore it.
      valid_retry_with_patch_results, retry_with_patch_successes, _ = (
          test_suite.retry_with_patch_results(caller_api))
      valid_retry_shards_results, retry_shards_successes, _ = (
          test_suite.shard_retry_with_patch_results(caller_api))
      if not (valid_retry_shards_results or valid_retry_with_patch_results):
        continue

      flaky_tests = set()
      if valid_retry_shards_results:
        flaky_tests = flaky_tests.union(
            potential_test_flakes & retry_shards_successes)
      if valid_retry_with_patch_results:
        flaky_tests = flaky_tests.union(
            potential_test_flakes & retry_with_patch_successes)

      if flaky_tests:
        suffix = 'with patch'
        # If we have invalid results on the initial run, but had valid results
        # on the retries, count the retried shards as flaky.
        if (not test_suite.has_valid_results(caller_api, 'with patch') and
            valid_retry_with_patch_results and valid_retry_shards_results):
          suffix = 'retry shards with patch'

        step_name = test_suite.name_of_step_for_suffix(suffix)
        step_layer_flakiness[step_name] = sorted(flaky_tests)

    potential_build_flakiness = {}
    for test_suite in test_suites:
      potential_test_flakes = self._findit_potential_test_flakes(caller_api,
                                                                 test_suite)

      # If the test suite was supposed to run retry with patch, then exclude all
      # tests that passed in retry with patch.
      if test_suite.should_retry_with_patch:
        valid_results, retry_with_patch_successes, _ = (
            test_suite.retry_with_patch_results(caller_api))
        if valid_results:
          potential_test_flakes = (
              potential_test_flakes - retry_with_patch_successes)

      valid_retry_shards_results, retry_shards_successes, _ = (
          test_suite.shard_retry_with_patch_results(caller_api))
      if valid_retry_shards_results:
        potential_test_flakes = (
            potential_test_flakes - retry_shards_successes)

      if potential_test_flakes:
        step_name = test_suite.name_of_step_for_suffix('with patch')
        potential_build_flakiness[step_name] = sorted(potential_test_flakes)

    # TODO(crbug.com/939063): Surface information about retried shards.
    if step_layer_flakiness or potential_build_flakiness:
      output = { 'Step Layer Flakiness' : step_layer_flakiness,
                 'Failing With Patch Tests That Caused Build Failure' :
                    potential_build_flakiness }
      step = caller_api.python.succeeding_step(
          'FindIt Flakiness', 'Metadata for FindIt post processing.')
      step.presentation.logs['step_metadata'] = (
          json.dumps(output, sort_keys=True, indent=2)
      ).splitlines()

  def _archive_retry_summary(self, retry_summary, dest_filename):
    """Archives the retry summary as JSON, storing it alongside the results
    from the first run."""
    script = self.m.chromium.repo_resource(
        'scripts', 'slave', 'chromium', 'archive_layout_test_retry_summary.py')
    args = [
        '--retry-summary-json', self.m.json.input(retry_summary),
        '--build-number', self.m.buildbucket.build.number,
        '--builder-name', self.m.buildbucket.builder_name,
        '--gs-bucket', 'gs://chromium-layout-test-archives',
        '--dest-filename', dest_filename
    ]
    args += self.m.build.slave_utils_args
    self.m.build.python('archive_retry_summary', script, args)

  def create_results_from_json(self, data):
    return TestResults(data)

  @recipe_util.returns_placeholder
  def test_results(self, add_json_log=True):
    """A placeholder which will expand to '/tmp/file'.

    The recipe must provide the expected --json-test-results flag.

    The test_results will be an instance of the TestResults class.
    """
    return TestResultsOutputPlaceholder(self, add_json_log)

  @recipe_util.returns_placeholder
  def gtest_results(self, add_json_log=True):
    """A placeholder which will expand to
    '--test-launcher-summary-output=/tmp/file'.

    Provides the --test-launcher-summary-output flag since --flag=value
    (i.e. a single token in the command line) is the required format.

    The test_results will be an instance of the GTestResults class.
    """
    return GTestResultsOutputPlaceholder(self, add_json_log)

class TestGroup(object):
  def __init__(self, tests):
    self._tests = tests

  def pre_run(self, caller_api, suffix): # pragma: no cover
    """Executes the |pre_run| method of each test.

    Args:
      caller_api - The api object given by the caller of this module.
      suffix - The test name suffix.
    """
    raise NotImplementedError()

  def run(self, caller_api, suffix): # pragma: no cover
    """Executes the |run| method of each test.

    Args:
      caller_api - The api object given by the caller of this module.
      suffix - The test name suffix.
    """
    raise NotImplementedError()

  def _run_func(self, test, test_func, caller_api, suffix, raise_on_failure):
    """Runs a function on a test, and handles errors appropriately."""
    try:
      test_func(caller_api, suffix)
    except caller_api.step.InfraFailure:
      raise
    except caller_api.step.StepFailure:
      if raise_on_failure and test.abort_on_failure:
        raise


class LocalGroup(TestGroup):
  def __init__(self, tests):
    super(LocalGroup, self).__init__(tests)

  def pre_run(self, caller_api, suffix):
    """Executes the |pre_run| method of each test."""
    for t in self._tests:
      self._run_func(t, t.pre_run, caller_api, suffix, False)

  def run(self, caller_api, suffix):
    """Executes the |run| method of each test."""
    for t in self._tests:
      self._run_func(t, t.run, caller_api, suffix, True)


class SwarmingGroup(TestGroup):
  def __init__(self, tests):
    super(SwarmingGroup, self).__init__(tests)
    self._task_ids_to_test = {}

  def pre_run(self, caller_api, suffix):
    """Executes the |pre_run| method of each test."""
    for t in self._tests:
      self._run_func(t, t.pre_run, caller_api, suffix, False)
      task = t.get_task(suffix)
      if not task:
        continue

      task_ids = tuple(task.get_task_ids())
      self._task_ids_to_test[task_ids] = t

  def run(self, caller_api, suffix):
    """Executes the |run| method of each test."""
    attempts = 0
    while self._task_ids_to_test:
      if len(self._task_ids_to_test) == 1:
        # We only have one test left to collect, just collect it normally.
        key = list(self._task_ids_to_test.keys())[0]
        test = self._task_ids_to_test[key]
        self._run_func(test, test.run, caller_api, suffix, True)
        del self._task_ids_to_test[key]
        break

      finished_sets, attempts = (
          caller_api.chromium_swarming.wait_for_finished_task_set(
              list(self._task_ids_to_test), suffix=(
                  (' (%s)' % suffix) if suffix else ''), attempts=attempts))
      for task_set in finished_sets:
        test = self._task_ids_to_test[tuple(task_set)]
        self._run_func(test, test.run, caller_api, suffix, True)
        del self._task_ids_to_test[task_set]

    # Testing this suite is hard, because the step_test_data for get_states
    # means that it's hard to force it to never return COMPLETED for tasks. This
    # shouldn't happen anyways, so hopefully not testing this will be fine.
    if self._task_ids_to_test: # pragma: no cover
      # Something weird is going on, just collect tasks like normal, and log a
      # warning.
      result = caller_api.python.succeeding_step(
          'swarming tasks.get_states issue', (
          'swarming tasks.get_states seemed to indicate that all tasks for this'
          ' build were finished collecting, but the recipe thinks the following'
          ' tests still need to be collected:\n%s\nSomething is probably wrong'
          ' with the swarming server. Falling back on the old collection logic.'
          % ', '.join(
              test.name for test in self._task_ids_to_test.values())))
      result.presentation.status = caller_api.step.WARNING

      for test in self._task_ids_to_test.values():
        # We won't collect any already collected tasks, as they're removed from
        # self._task_ids_to_test
        self._run_func(test, test.run, caller_api, suffix, True)
