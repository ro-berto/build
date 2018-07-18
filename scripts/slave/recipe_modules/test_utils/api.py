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
    overflow_line = '... %d more ...' % (len(failures) - limit)
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
      tests - iterable of objects implementing the Test interface above
      suffix - custom suffix, e.g. "with patch", "without patch" indicating
               context of the test run
    Returns:
      The list of failed tests.
    """
    failed_tests = []

    with self.m.step.nest('test_pre_run'):
      for t in tests:
        try:
          t.pre_run(caller_api, suffix)
        except caller_api.step.InfraFailure:
          raise
        except caller_api.step.StepFailure:
          failed_tests.append(t)

    for t in tests:
      try:
        t.run(caller_api, suffix)
      except caller_api.step.InfraFailure:
        raise
      except caller_api.step.StepFailure:
        failed_tests.append(t)
        if t.abort_on_failure:
          raise

    return failed_tests

  def run_tests_with_patch(self, caller_api, tests):
    failing_tests = self.run_tests(caller_api, tests, 'with patch')
    failing_test_names = set(f.name for f in failing_tests)
    with self.m.step.defer_results():
      for t in tests:
        if not t.has_valid_results(caller_api, 'with patch'):
          self._invalid_test_results(t)
          failing_test_names.discard(t)
        elif t.failures(caller_api, 'with patch'):
          if t.name not in failing_test_names:
            failing_tests.append(t)
            failing_test_names.add(t.name)
    return failing_tests

  def determine_new_failures(self, caller_api, tests, deapply_patch_fn):
    """
    Utility function for running steps with a patch applied, and retrying
    failing steps without the patch. Failures from the run without the patch are
    ignored.

    Args:
      caller_api - caller's recipe API; this is needed because self.m here
                   is different than in the caller (different recipe modules
                   get injected depending on caller's DEPS vs. this module's
                   DEPS)
      tests - iterable of objects implementing the Test interface above
      deapply_patch_fn - function that takes a list of failing tests
                         and undoes any effect of the previously applied patch
    """
    # Convert iterable to list, since it is enumerated multiple times.
    tests = list(tests)

    failing_tests = self.run_tests_with_patch(caller_api, tests)
    if not failing_tests:
      return

    try:
      result = deapply_patch_fn(failing_tests)
      self.run_tests(caller_api, failing_tests, 'without patch')
      return result
    except Exception as e:
      # This except is here to try to debug a strange error. Builds like
      # https://ci.chromium.org/p/chromium/builders/luci.chromium.try/mac_chromium_rel_ng/80909
      # seem to be failing before they run any steps to de-apply the patch. The
      # hypothesis is that an exception is being thrown and ignored due to the
      # defer_results() call below.
      text = 'exception occured while de-applying patch\n%s' % (str(e))
      step = self.m.python.succeeding_step('deapply_failure', text)
      step.presentation.status = self.m.step.WARNING
      step.presentation.logs['exception'] = [
          str(e), '\n', self.m.traceback.format_exc()]
      raise
    finally:
      with self.m.step.defer_results():
        for t in failing_tests:
          self._summarize_retried_test(caller_api, t)

  def _invalid_test_results(self, test):
    self.m.tryserver.set_invalid_test_results_tryjob_result()
    self.m.python.failing_step(test.name, self.INVALID_RESULTS_MAGIC)

  def _summarize_retried_test(self, caller_api, test):
    """Summarizes test results and exits with a failing status if there were new
    failures."""
    if not test.has_valid_results(caller_api, 'without patch'):
      self._invalid_test_results(test)

    ignored_failures = set(test.failures(caller_api, 'without patch'))
    new_failures = (
      set(test.failures(caller_api, 'with patch')) - ignored_failures)

    self.m.tryserver.add_failure_reason({
      'test_name': test.name,
      'new_failures': sorted(new_failures),
    })

    step_name = '%s (retry summary)' % test.name
    step_text = self.format_step_text([
        ['failures:', new_failures],
        ['ignored:', ignored_failures]
    ])
    try:
      if new_failures:
        self.m.python.failing_step(step_name, step_text)
      else:
        self.m.python.succeeding_step(step_name, step_text)
    finally:
      if new_failures:
        self.m.tryserver.set_test_failure_tryjob_result()
      elif ignored_failures:
        self.m.step.active_result.presentation.status = self.m.step.WARNING

      # TODO(crbug/706192): Remove the check for webkit_tests, once this step
      # name no longer exists.
      if test.name in ('webkit_tests', 'webkit_layout_tests'):
        self._archive_retry_summary({
            'failures': sorted(new_failures),
            'ignored': sorted(ignored_failures)
        })

  def _archive_retry_summary(self, retry_summary):
    """Archives the retry summary as JSON, storing it alongside the results
    from the first run."""
    script = self.m.chromium.package_repo_resource(
        'scripts', 'slave', 'chromium', 'archive_layout_test_retry_summary.py')
    args = [
        '--retry-summary-json', self.m.json.input(retry_summary),
        '--build-number', self.m.properties['buildnumber'],
        '--builder-name', self.m.properties['buildername'],
        '--gs-bucket', 'gs://chromium-layout-test-archives',
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
