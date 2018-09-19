# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import itertools

from recipe_engine import recipe_api
from recipe_engine import util as recipe_util

from .util import GTestResults, TestResults

# TODO(luqui): Destroy this DEPS hack.
import DEPS
JsonOutputPlaceholder = DEPS['json'].api.JsonOutputPlaceholder


class TestResultsOutputPlaceholder(JsonOutputPlaceholder):
  def result(self, presentation, test):
    ret = super(TestResultsOutputPlaceholder, self).result(presentation, test)
    return TestResults(ret)


class GTestResultsOutputPlaceholder(JsonOutputPlaceholder):
  def result(self, presentation, test):
    ret = super(GTestResultsOutputPlaceholder, self).result(presentation, test)
    return GTestResults(ret)

class TestUtilsApi(recipe_api.RecipeApi):

  # Some test runners (such as run_web_tests.py and python tests) returns the
  # number of failures as the return code. They need to cap the return code at
  # 101 to avoid overflow or colliding with reserved values from the shell.
  MAX_FAILURES_EXIT_STATUS = 101

  # This magic string is depended on by other infra tools.
  INVALID_RESULTS_MAGIC = 'TEST RESULTS WERE INVALID'

  def __init__(self, max_reported_gtest_failures, *args, **kwargs):
    super(TestUtilsApi, self).__init__(*args, **kwargs)
    self._max_reported_gtest_failures = max_reported_gtest_failures

  @staticmethod
  def limit_failures(failures, limit):
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

    The max_reported_gtest_failures property modifies this behavior by limiting
    the number of tests that will appear in the step text and have their logs
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
      failures, text_failures = self.limit_failures(
          r.failures, self._max_reported_gtest_failures)
      for f in failures:
        p.logs[f] = r.logs[f]
      p.step_text += self.format_step_text([
          ['failures:', text_failures],
      ])
    return r

  def run_tests(self, caller_api, tests, suffix):
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
    Returns:
      The list of failed tests.


    """
    if not hasattr(caller_api, 'swarming'):
      self.m.python.failing_step(
          'invalid caller_api',
          'caller_api must include the swarming recipe module')

    local_tests = []
    swarming_tests = []
    for test in tests:
      # Some callers don't deps in chromium_tests. That's fine, this is just a
      # temporary condition for now.
      is_staging = (
          hasattr(caller_api, 'chromium_tests') and
          caller_api.chromium_tests.c and caller_api.chromium_tests.c.staging)
      if is_staging and isinstance(
          test, caller_api.chromium_tests.steps.SwarmingTest):
        swarming_tests.append(test)
      else:
        local_tests.append(test)

    groups = [LocalGroup(local_tests), SwarmingGroup(swarming_tests)]
    with self.m.step.nest('test_pre_run'):
      for group in groups:
        group.pre_run(caller_api, suffix)

    failed_tests = []
    for group in groups:
      failed_tests.extend(group.run(caller_api, suffix))

    return failed_tests

  def run_tests_with_patch(self, caller_api, tests, invalid_is_fatal):
    """Run tests and returns failures.

    Args:
      caller_api: The api object given by the caller of this module.
      tests: A list of test suites to run with the patch.
      invalid_is_fatal: Whether invalid test results should be treated as a
                        fatal failing step.

    Returns: A list of test suites that either have invalid results or failing
    tests.
    """
    failing_tests = self.run_tests(caller_api, tests, 'with patch')
    failing_test_names = set(f.name for f in failing_tests)
    with self.m.step.defer_results():
      for t in tests:
        valid_results, failures = t.failures_or_invalid_results(
            caller_api, 'with patch')

        if not valid_results:
          self._invalid_test_results(t, fatal=invalid_is_fatal)

        # No need to re-add a test_suite that is already in the return list.
        if t in failing_tests:
          continue

        if not valid_results or failures:
          failing_tests.append(t)
    return failing_tests

  def _invalid_test_results(self, test, fatal):
    """Marks test results as invalid.

    If |fatal| is True, emits a failing step. Otherwise emits a succeeding step.
    """
    self.m.tryserver.set_invalid_test_results_tryjob_result()

    # Record a step with INVALID_RESULTS_MAGIC, which chromium_try_flakes uses
    # for analysis.
    if fatal:
      self.m.python.failing_step(test.name, self.INVALID_RESULTS_MAGIC)
    else:
      self.m.python.succeeding_step(test.name, self.INVALID_RESULTS_MAGIC)

  def _summarize_new_and_ignored_failures(self, test, new_failures, ignored_failures, suffix, emit_failing_step):
    """Summarizes new and ignored failures in the test_suite |test|.

    Args:
      test: A test suite that's been retried.
      new_failures: Failures that are potentially caused by the patched CL.
      ignored_failures: Failures that are not caused by the patched CL.
      suffix: Should be either 'retry with patch summary' or 'retry summary'.
      emit_failing_step: Whether to emit a failing step.

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

    if test.name == 'webkit_layout_tests':
      dest_file = '%s.json' % suffix.replace(' ', '_')
      self._archive_retry_summary({
          'failures': sorted(new_failures),
          'ignored': sorted(ignored_failures)
      }, dest_file)

    step_name = '%s (%s)' % (test.name, suffix)
    step_text = self.format_step_text([
        ['failures:', new_failures],
        ['ignored:', ignored_failures]
    ])

    if new_failures and emit_failing_step:
      try:
        self.m.python.failing_step(step_name, step_text)
      finally:
        self.m.tryserver.set_test_failure_tryjob_result()
    else:
      self.m.python.succeeding_step(step_name, step_text)
      if ignored_failures:
        self.m.step.active_result.presentation.status = self.m.step.WARNING

    return not bool(new_failures)


  def summarize_test_with_patch_deapplied(self, caller_api, test,
                                          emit_failing_step=True):
    """Summarizes test results after a CL has been retried with patch deapplied.

    Args:
      emit_failing_step: Whether new failures should emit a failing step.

    Returns:
      A Boolean describing whether the retry succeeded. Which is to say, all
      tests that failed in the original run also failed in the retry, which
      suggests that the error is due to an issue with top of tree, and should
      not cause the CL to fail.
    """
    valid_results, failures = test.failures_or_invalid_results(
        caller_api, 'without patch')

    if not valid_results:
      self._invalid_test_results(test, fatal=emit_failing_step)

    # If there are invalid results from the deapply patch step, treat this as if
    # all tests passed which prevents us from ignoring any test failures from
    # 'with patch'.
    ignored_failures = set(failures) if valid_results else set()

    valid_results, failures = test.failures_or_invalid_results(
        caller_api, 'with patch')
    if valid_results:
      new_failures = set(failures) - ignored_failures
    else:
      new_failures = set(['all initial tests failed'])

    return self._summarize_new_and_ignored_failures(
        test, new_failures, ignored_failures,
        'retry summary', emit_failing_step)

  def summarize_test_with_patch_reapplied(self, caller_api, test):
    """Summarizes test results after a CL has been retried with patch reapplied.

    Returns:
      A Boolean describing whether the retry succeeded. Which is to say, whether
      there are tests that failed in 'with patch' and 'retry with patch', but
      not in 'without patch'.
    """
    valid_results, new_failures = test.failures_or_invalid_results(
        caller_api, 'retry with patch')

    # We currently do not attempt to recover from invalid test results on the
    # retry. Record a failing step with INVALID_RESULTS_MAGIC, which
    # chromium_try_flakes uses for analysis.
    if not valid_results:
      self._invalid_test_results(test, fatal=True)

    # Assuming both 'with patch' and 'retry with patch' produced valid results,
    # look for the intersection of failures.
    valid_results, initial_failures = test.failures_or_invalid_results(
        caller_api, 'with patch')
    if valid_results:
      repeated_failures = new_failures & initial_failures
    else:
      repeated_failures = new_failures

    # Assuming 'without patch' produced valid results, subtract those from
    # repeated failures, as they're likely problems with tip of tree.
    valid_results, without_patch_failures = test.failures_or_invalid_results(
        caller_api, 'without patch')
    if valid_results:
      new_failures = repeated_failures - without_patch_failures
      ignored_failures = without_patch_failures
    else:
      new_failures = repeated_failures
      ignored_failures = set()

    return self._summarize_new_and_ignored_failures(test, new_failures,
        ignored_failures, 'retry with patch summary', emit_failing_step=True)

  def _archive_retry_summary(self, retry_summary, dest_filename):
    """Archives the retry summary as JSON, storing it alongside the results
    from the first run."""
    script = self.m.chromium.package_repo_resource(
        'scripts', 'slave', 'chromium', 'archive_layout_test_retry_summary.py')
    args = [
        '--retry-summary-json', self.m.json.input(retry_summary),
        '--build-number', self.m.properties['buildnumber'],
        '--builder-name', self.m.properties['buildername'],
        '--gs-bucket', 'gs://chromium-layout-test-archives',
        '--dest-filename', dest_filename
    ]
    args += self.m.build.slave_utils_args
    self.m.build.python('archive_retry_summary', script, args)

  def create_results_from_json(self, data):
    return TestResults(data)

  def create_results_from_json_if_needed(self, data):
    if data is None:
      raise TypeError('Invalid data given')
    if isinstance(data, TestResults):
      return data
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
    self._failed_tests = []

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
    Returns:
      A list of failed tests.
    """
    raise NotImplementedError()

  def _run_func(self, test, test_func, caller_api, suffix, raise_on_failure):
    """Runs a function on a test, and handles errors appropriately."""
    try:
      test_func(caller_api, suffix)
    except caller_api.step.InfraFailure:
      raise
    except caller_api.step.StepFailure:
      self._failed_tests.append(test)
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

    return self._failed_tests


class SwarmingGroup(TestGroup):
  def __init__(self, tests):
    super(SwarmingGroup, self).__init__(tests)
    self._all_task_ids = set()
    self._task_ids_to_test = {}

  def pre_run(self, caller_api, suffix):
    """Executes the |pre_run| method of each test."""
    for t in self._tests:
      self._run_func(t, t.pre_run, caller_api, suffix, False)
      task = t.get_task(suffix)

      task_ids = frozenset(task.get_task_ids())
      self._all_task_ids.update(task_ids)
      self._task_ids_to_test[task_ids] = t

  def run(self, caller_api, suffix):
    """Executes the |run| method of each test."""
    unfinished_tasks = set(self._all_task_ids)
    attempts = 0
    while unfinished_tasks:
      if len(self._task_ids_to_test.values()) == 1:
        # We only have one test left to collect, just collect it normally.
        key = list(self._task_ids_to_test.keys())[0]
        test = self._task_ids_to_test[key]
        self._run_func(test, test.run, caller_api, suffix, True)
        del self._task_ids_to_test[key]
        break

      collected = False

      states = caller_api.swarming.get_states(
          list(unfinished_tasks), suffix=(
              (' (%s)' % suffix) if suffix else ''))
      for task_id, state in states.items():
        if state not in ('PENDING', 'RUNNING'):
          unfinished_tasks.discard(task_id)

      for task_ids, test in self._task_ids_to_test.items():
        # Some swarming tasks are done. We want to make sure that all of the
        # swarming tasks for a test are finished before we run collect on it.
        # If any task is still unfinished, don't collect the task.
        if unfinished_tasks.intersection(task_ids):
          continue

        collected = True
        self._run_func(test, test.run, caller_api, suffix, True)
        del self._task_ids_to_test[task_ids]

      # If we collected something, it possible more tasks are waiting to be
      # collected. Try collecting immediately, rather than sleeping.
      if collected:
        continue

      attempts += 1
      time_to_sleep_sec = 2 ** attempts
      # Cap the sleep time at 2 minutes. Waiting longer than that could start to
      # impact the actual cycle time of the builder; if we wait for 16 minutes,
      # and (potentially) the final task finished one minute into that sleep,
      # we'd waste 15 minutes of time just sitting there. Ideally this would be
      # interrupt driven, rather than polling, but that's hard given the current
      # architecture of recipes.
      time_to_sleep_sec = min(time_to_sleep_sec, 2 * 60)
      caller_api.time.sleep(time_to_sleep_sec)

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

      for task_ids, test in self._task_ids_to_test.items():
        # We won't collect any already collected tasks, as they're removed from
        # self._task_ids_to_test
        self._run_func(test, test.run, caller_api, suffix, True)

    return self._failed_tests

