# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import itertools
import json
import urlparse

from recipe_engine import recipe_api
from recipe_engine import util as recipe_util

from . import canonical
from .util import GTestResults, TestResults

from PB.go.chromium.org.luci.resultdb.proto.v1 import (test_result as
                                                       test_result_pb2)

from RECIPE_MODULES.build.chromium_tests import steps
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
    * 'retry shards with patch'
    * 'without patch'

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

  # Header for test failures that caused the build to fail.
  NEW_FAILURES_TEXT = 'Tests failed with patch, and caused build to fail:'

  # Header for ignored failures due to without patch.
  IGNORED_FAILURES_TEXT = (
      'Tests failed with patch, but ignored as they also fail without patch:')

  # Header for ignored failures due to that they're known to be flaky.
  IGNORED_FLAKES_TEXT = (
      'Tests failed with patch, but ignored as they are known to be flaky:')

  def __init__(self, properties, *args, **kwargs):
    super(TestUtilsApi, self).__init__(*args, **kwargs)
    self._max_reported_failures = properties.max_reported_failures or 30

    # This flag provides a escape-hatch to disable the feature of exonerating
    # flaky failures and make everything fall back to original behaviors when
    # there is a bug or outage. When landing the CL that flips the switch, it
    # should be TBRed and No-tried to minimize the negative impact of an outage.
    self._should_exonerate_flaky_failures = True

    # Skip retrying if there are >= N test suites with test failures. This most
    # likely indicates a problem with the CL itself instead of being caused by
    # flaky tests when N is large.
    # 5 is chosen because it's a conscious tradeoff between CQ cycle time and
    # false rejection rate, and a study conducted in http://bit.ly/37CSyBA shows
    # that 90th percentile cycle time can be improved by 2.2% with a loss of
    # 0.15% false rejection rate.
    self._min_failed_suites_to_skip_retry = (
        properties.min_failed_suites_to_skip_retry or 5)

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
    overflow_line = '... %d more (%d total) ...' % (len(failures) - limit,
                                                    len(failures))
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
        log_name = '%s: %s (status %s)' % (prefix, f, ','.join(
            set(r.raw_results[f])))
        p.logs[log_name] = [
            "Test '%s' completed with the following status(es): '%s'" %
            (f, '\',\''.join(r.raw_results[f])),
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
      non_notrun_failures_set = set([
          f for f in deterministic_failures_set
          if set(r.raw_results[f]) != {'NOTRUN'}
      ])

      # If the deterministic_failures_set has other state of failures other
      # than NOTRUN, only report those failures and skip reporting the NOTRUN
      # failures as they will probably not be the 'actual' failures
      if non_notrun_failures_set:
        deterministic_failures_set = non_notrun_failures_set

      deterministic_failures, deterministic_failures_text = (
          self.limit_failures(sorted(deterministic_failures_set)))
      flaky_failures, flaky_failures_text = (
          self.limit_failures(sorted(flaky_failures_set)))
      for f in deterministic_failures:
        emit_log(f, 'Deterministic failure')
      for f in flaky_failures:
        emit_log(f, 'Flaky failure')

      p.step_text += self.format_step_text([
          [
              'deterministic failures [caused step to fail]:',
              deterministic_failures_text
          ],
          ['flaky failures [ignored]:', flaky_failures_text],
      ])
    return r

  # Runs a set of tests once.
  #
  # Used as a helper function by run_tests. See full documentation there.
  def _run_tests_once(self,
                      caller_api,
                      test_suites,
                      suffix,
                      sort_by_shard=False):
    local_test_suites = []
    swarming_test_suites = []
    for t in test_suites:
      if isinstance(t, steps.SwarmingTest):
        swarming_test_suites.append(t)
      else:
        local_test_suites.append(t)

    if sort_by_shard:
      # Trigger tests which have a large number of shards earlier. They usually
      # take longer to complete, and triggering take a few minutes, so this
      # should get us a few extra minutes of speed.
      swarming_test_suites.sort(key=lambda t: -t.shards)

    groups = [
        LocalGroup(local_test_suites),
        SwarmingGroup(swarming_test_suites)
    ]

    nest_name = 'test_pre_run (%s)' % suffix if suffix else 'test_pre_run'

    with self.m.step.nest(nest_name):
      for group in groups:
        group.pre_run(caller_api, suffix)

    for group in groups:
      group.run(caller_api, suffix)

    failed_test_suites = []
    invalid_results = []
    for t in test_suites:
      # Note that this is technically O(n^2). We expect n to be small.
      if not t.has_valid_results(suffix):
        invalid_results.append(t)
      elif t.deterministic_failures(suffix) and t not in failed_test_suites:
        failed_test_suites.append(t)

    if (self.m.buildbucket.build.builder.project != 'chromium' or
        self.m.buildbucket.build.builder.bucket not in ['ci', 'try']):
      # Only derives results on chromium ci/try builders.
      # Note: this is a temporary change for ResultDB to control the builders it
      # gets test results from.
      return invalid_results, failed_test_suites

    # Derives swarming test results to ResultDB.
    # The returned results are not being used yet.
    swarming_task_ids = []
    for t in swarming_test_suites:
      task = t.get_task(suffix)
      swarming_task_ids.extend(task.get_task_ids())

    derive_step_name = ('derive test results (%s)' % suffix
                        if suffix else 'derive test results')
    if len(swarming_task_ids) == 0:
      step_result = self.m.step('[skipped] %s' % derive_step_name, [])
      step_result.presentation.logs["stdout"] = [
          'No swarming test results to derive.'
      ]
      return invalid_results, failed_test_suites

    swarming_host = caller_api.chromium_swarming.swarming_server
    parsed = urlparse.urlparse(swarming_host)
    if parsed.scheme:
      swarming_host = parsed.netloc

    # Failure of these steps should not fail the build.
    # TODO(crbug.com/1021849): raise the failures instead of swallowing them.
    try:
      invocations = self.m.resultdb.chromium_derive(
          step_name=derive_step_name,
          swarming_host=swarming_host,
          task_ids=swarming_task_ids,
          variants_with_unexpected_results=True,
      )

      if not self.m.resultdb.enabled:
        # Checks if resultdb integration is enabled.
        # Temporary workaround to make sure led builds don't fail because of
        # this.
        # Should be removed when led v2 starts to create invocations.
        return invalid_results, failed_test_suites

      if suffix != 'without patch':
        # Include the derived invocations in the build's invocation.
        # Note that 'without patch' results are derived but not included in
        # the builds' invocation, since the results are not related to the
        # patch under test.
        include_step_name = ('include derived test results (%s)' % suffix
                             if suffix else 'include derived test results')
        self.m.resultdb.include_invocations(
            invocations.keys(), step_name=include_step_name)

      test_variants = self._test_variants_with_unexpected_results(
          invocations, suffix)

      step_name = 'exonerate unexpected passes'
      if suffix == 'without patch':
        step_name = 'exonerate unexpected without patch results'
      elif suffix:
        step_name = '%s (%s)' % (step_name, suffix)

      exonerations = self._test_exonerations_for_test_variants(
          test_variants, suffix)
      self.m.resultdb.exonerate(
          test_exonerations=exonerations,
          step_name=step_name,
      )
    except (self.m.step.InfraFailure,
            self.m.step.StepFailure):  # pragma: no cover
      pass

    return invalid_results, failed_test_suites

  def _test_variants_with_unexpected_results(self, invocations, suffix):
    """Gets test variants with unexpected results.

    This is a helper function to get test variants to exonerate.

    To be consistent with the current recipe logic at http://shortn/_KibEsLgpJK,
      - test variants with unexpected failures in (without patch) steps will be
      exonerated.
      - test variants with unexpected passes in any step will be exonerated.

    This is subject to change if other unexpected results besides above
    mentioned cases should also be exonerated.

    Args:
      invocations (dict): A dict {invocation_id: api.resultdb.Invocation}.
        Please refer to go/resultdb-concepts for more details.
        An example below:
        {
          'invocation_id': api.resultdb.Invocation(
              proto=invocation_pb2.Invocation(
                  state=invocation_pb2.Invocation.FINALIZED
              ),
              test_results=[
                  test_result_pb2.TestResult(
                      test_id='ninja://chromium/tests:browser_tests/Test',
                      variant={'def': {
                          'key1': 'value1',
                          'key2': 'value2'
                      }},
                      expected=False,
                      status=test_result_pb2.FAIL,
                  ),
              ],
          ),
        }
      suffix (str): suffix to add to the step name.

    Returns:
      A dict of test variants in the format:
       {
         'test_id1': [
           {
             'def': {
               'key1': 'value1',
               'key2': 'value2',
             }
           }
         ],
         'test_id2': [
           {
             'def': {
               'key3': 'value3',
             }
           }
         ]
       }
    """
    res = {}
    for inv in invocations.values():
      for tr in inv.test_results:
        if suffix == 'without patch':
          # Unexpected results including unexpected failures in without patch
          # steps will not cause a build failure.
          # See http://shortn/_KibEsLgpJK
          should_exonerate = not tr.expected
        else:
          # Unexpected passes do not cause a build failure.
          should_exonerate = (not tr.expected and
                              tr.status == test_result_pb2.PASS)
        if not should_exonerate:
          continue

        res.setdefault(tr.test_id, [])
        found = False
        for v in res[tr.test_id]:
          # TODO(crbug.com/1076650): use variant_hash when it's exposed to proto
          if v == tr.variant:
            found = True
            break

        if not found:
          res[tr.test_id].append(tr.variant)

    return res

  def _test_exonerations_for_test_variants(self, test_variants, suffix):
    """Gets test exonerations for ResultDB test variants.

    Args:
      test_variants (dict): A dict of test variants in the format.
        See returned value of _test_variants_with_unexpected_failures.
      suffix (str): suffix to add to the step name.

    Returns:
      A list of test_result_pb2.TestExoneration.
    """
    explanation_html = 'Unexpected passes do not cause a build failure'
    if suffix == 'without patch':
      explanation_html = (
          'Unexpected results in (without patch) steps do not cause a build'
          ' failure, including unexpected failures (http://shortn/_KibEsLgpJK)')
    ret = []
    for test_id, variants in test_variants.iteritems():
      for v in variants:
        ret.append(
            test_result_pb2.TestExoneration(
                test_id=test_id,
                variant=v,
                # TODO(crbug.com/1076096): add deep link to the Milo UI to
                #  display the exonerated test results.
                explanation_html=explanation_html,
            ))
    return ret

  def _query_and_mark_flaky_failures(self, failed_test_suites):
    """Queries and marks failed tests that are already known to be flaky.

    This method updates |failed_test_suites| in place, which will be used to
    skip retrying known flaky failures. A considered alternative is to directly
    modify the set of deterministic failures, but wasn't chosen because it's
    more desirable to be able to distinguish a skipped/forgiven failure from a
    success so that they can be properly surfaced.

    This feature is controlled by the should_exonerate_flaky_failures property,
    which allows switch on/off with ease and flexibility.

    Args:
      failed_test_suites ([steps.Test]): A list of failed test suites to check.
    """
    if not failed_test_suites:
      return

    tests_to_check = []
    for test_suite in failed_test_suites:
      tests = []
      for t in set(test_suite.deterministic_failures('with patch')):
        tests.append({
            'step_ui_name': test_suite.name_of_step_for_suffix('with patch'),
            'test_name': t,
        })

      if len(tests) > 100:
        # Bail out if there are too many failed tests because:
        # 1. It's unlikely they're all legitimate flaky failures.
        # 2. Avoid overloading the service.
        continue

      tests_to_check.extend(tests)

    if not tests_to_check:
      return

    builder = self.m.buildbucket.build.builder
    flakes_input = {
        'project': builder.project,
        'bucket': builder.bucket,
        'builder': builder.builder,
        'tests': tests_to_check,
    }

    result = self.m.python(
        'query known flaky failures on CQ',
        self.resource('query_cq_flakes.py'),
        args=[
            '--input-path',
            self.m.json.input(flakes_input),
            '--output-path',
            self.m.json.output(),
        ],
        infra_step=True,
        # Failing to query data from the service for any reason results in a
        # step with infra failure, but doesn't fail the build to avoid
        # affecting developers from landing their code, and the recipe will
        # fall back to the original behavior to retrying failed tests in case
        # of any issue.
        ok_ret=('any'))

    result.presentation.logs['input'] = json.dumps(flakes_input, indent=4)
    result.presentation.logs['output'] = json.dumps(
        result.json.output, indent=4)

    if result.exc_result.retcode != 0:
      result.presentation.step_text = 'Failed to get known flakes'
      return

    if not result.json.output:
      return

    if 'flakes' not in result.json.output:
      result.presentation.step_text = 'Response is ill-formed'
      return

    test_suite = None
    for flake in result.json.output['flakes']:
      if ('affected_gerrit_changes' not in flake or
          'monorail_issue' not in flake or 'test' not in flake or
          'step_ui_name' not in flake['test'] or
          'test_name' not in flake['test']):
        # Response is ill-formed. Don't expect to ever happen, but have this
        # check in place just in case.
        result.presentation.step_text = 'Response is ill-formed'
        return

      for t in failed_test_suites:
        if (t.name_of_step_for_suffix('with patch') == flake['test']
            ['step_ui_name']):
          t.add_known_flaky_failure(flake['test']['test_name'],
                                    flake['monorail_issue'])
          break

  def run_tests(self,
                caller_api,
                test_suites,
                suffix,
                sort_by_shard=False,
                retry_failed_shards=False,
                retry_invalid_shards=False):
    """Runs a list of test suites and returns the failed ones.

    If retry_[failed|invalid]_shards is true, this method retries shards that
    have deterministic failures or invalid results. Additionally, if the
    |_should_exonerate_flaky_failures| property is true, this method skips
    retrying deterministic failures that are already known to be flaky on ToT.

    Args:
      caller_api - caller's recipe API; this is needed because self.m here
                   is different than in the caller (different recipe modules
                   get injected depending on caller's DEPS vs. this module's
                   DEPS)
                   This must include the 'swarming' recipe module, in order to
                   use the grouping logic in this method. Unfortunately we can't
                   import this module in the test_utils module, as it would
                   cause a circular dependency.
      test_suites - iterable of objects implementing the steps.Test interface.
      suffix - custom suffix, e.g. "with patch", "without patch" indicating
               context of the test run
      sort_by_shard - sort the order of triggering depends on the number of
                      shards.
      retry_failed_shards: If true, attempts to retry failed shards of swarming
                           tests, typically used with retry_invalid_shards.
      retry_invalid_shards: If true, attempts to retry shards of swarming tests
                            without valid results.
    Returns:
      A tuple of (list of test suites with invalid results,
                  list of test suites which failed including invalid results)
    """
    if not hasattr(caller_api, 'chromium_swarming'):
      self.m.python.failing_step(
          'invalid caller_api',
          'caller_api must include the chromium_swarming recipe module')
    invalid_test_suites, failed_test_suites = self._run_tests_once(
        caller_api, test_suites, suffix, sort_by_shard=sort_by_shard)

    if self.m.tryserver.is_tryserver and len(
        failed_test_suites) >= self._min_failed_suites_to_skip_retry:
      result = self.m.python.succeeding_step(
          'skip retrying because there are >= %d test suites with test '
          'failures and it most likely indicate a problem with the CL' %
          self._min_failed_suites_to_skip_retry, '')
      result.presentation.status = self.m.step.FAILURE
      return invalid_test_suites, invalid_test_suites + failed_test_suites

    if suffix == 'with patch' and self._should_exonerate_flaky_failures:
      # If *all* the deterministic failures are known flaky tests, a test suite
      # will not be considered failure anymore, and thus will not be retried.
      #
      # A long as there is at least one non-flaky failure, all the failed shards
      # will be retried, including those due to flaky failures, and the reason
      # is that existing APIs don't allow associating test failures with shard
      # indices. One could implement such a connection, but the cost is high,
      # while return is very low from both the CQ cycle time and resource usage
      # perspective.
      self._query_and_mark_flaky_failures(failed_test_suites)
      for t in failed_test_suites[:]:
        if not t.known_flaky_failures:
          continue

        if (set(
            t.deterministic_failures('with patch')) == t.known_flaky_failures):
          failed_test_suites.remove(t)

    failed_and_invalid_suites = list(
        set(failed_test_suites + invalid_test_suites))

    if retry_failed_shards or retry_invalid_shards:
      suites_to_retry = set()
      if retry_failed_shards:
        suites_to_retry.update(failed_test_suites)
      if retry_invalid_shards:
        suites_to_retry.update(invalid_test_suites)

      # Assume that non swarming test retries probably won't help.
      swarming_test_suites = [t for t in suites_to_retry if t.runs_on_swarming]
      if swarming_test_suites:
        retry_suffix = 'retry shards'
        if suffix:
          retry_suffix += ' ' + suffix
        new_swarming_invalid_suites, _ = self._run_tests_once(
            caller_api, swarming_test_suites, retry_suffix, sort_by_shard=True)

        # For swarming test suites, if we have valid test results from one of
        # the runs of a test suite, then that test suite by definition doesn't
        # have invalid test results.
        # For non-swarming test suites, becuase they don't get retried in
        # 'retry shards with patch' steps, invalid non-swarming test suites are
        # still invalid.
        non_swarming_invalid_suites = [
            t for t in invalid_test_suites if not t.runs_on_swarming
        ]
        invalid_test_suites = list(
            set(invalid_test_suites).intersection(
                set(new_swarming_invalid_suites))) + non_swarming_invalid_suites

        # Some suites might be passing now, since we retried some tests. Remove
        # any suites which are now fully passing.
        # with_patch_failures_including_retry appropriately takes 'retry shards
        # with patch' and 'with patch' runs into account.
        #
        # Also take known flaky tests into consideration because it is possible
        # that both the original and retry runs fail due to the same flaky test.
        def _still_failing(suite):
          valid, failures = suite.failures_including_retry(suffix)
          return (not valid) or failures

        failed_and_invalid_suites = [
            t for t in failed_and_invalid_suites if _still_failing(t)
        ]

    return invalid_test_suites, failed_and_invalid_suites

  def run_tests_with_patch(self,
                           caller_api,
                           test_suites,
                           retry_failed_shards=False):
    """Runs tests and returns failures.

    Args:
      caller_api: The api object given by the caller of this module.
      test_suites - iterable of objects implementing the steps.Test interface.
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
        caller_api,
        test_suites,
        'with patch',
        sort_by_shard=True,
        retry_failed_shards=retry_failed_shards,
        retry_invalid_shards=retry_failed_shards)

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
      self, test_suite, new_failures, ignored_failures, ignored_flakes,
      new_failures_text, ignored_failures_text, ignored_flakes_text):
    """Summarizes new and ignored failures and flakes in the test_suite.

    Args:
      test_suite: A test suite that's been retried.
      new_failures: Failures that are potentially caused by the patched CL.
      ignored_failures: Failures that are not caused by the patched CL.
      ignored_flakes: Failures due to known flakes unrelated to the patched CL.
      new_failures_text: A user-visible string describing new_failures.
      ignored_failures_text: A user-visible string describing ignored_failures.
      ignored_flakes_text: A user-visible string describing ignored_flakes.

    Returns:
      A Boolean describing whether the retry succeeded. Which is to say, the
      patched CL did not cause the test suite to have deterministically failing
      tests.
    """
    new_failures = sorted(new_failures)
    ignored_failures = sorted(ignored_failures)
    ignored_flakes = sorted(ignored_flakes)

    suffix = 'test results summary'
    if test_suite.name == 'blink_web_tests':
      dest_file = '%s.json' % suffix.replace(' ', '_')
      self._archive_test_results_summary({
          'failures': new_failures,
          'ignored': ignored_failures
      }, dest_file)

    step_name = '%s (%s)' % (test_suite.name, suffix)
    _, truncated_new_failures = self.limit_failures(new_failures)
    _, truncated_ignored_failures = self.limit_failures(ignored_failures)
    _, truncated_ignored_flakes = self.limit_failures(ignored_flakes)
    step_text = self.format_step_text(
        [[new_failures_text, truncated_new_failures],
         [ignored_failures_text, truncated_ignored_failures],
         [ignored_flakes_text, truncated_ignored_flakes]])

    if ignored_flakes:
      step_text += ('<br/>If the mentioned known flaky tests are incorrect, '
                    'please file a bug at: http://bit.ly/37I61c2<br/>')

    result = self.m.python.succeeding_step(step_name, step_text)
    if new_failures:
      result.presentation.logs[
          'failures caused build to fail'] = self.m.json.dumps(
              new_failures, indent=2).split('/n')
    if ignored_failures:
      result.presentation.logs[
          'failures ignored as they also fail without patch'] = (
              self.m.json.dumps(ignored_failures, indent=2).split('/n'))
    if ignored_flakes:
      result.presentation.logs[
          'failures ignored as they are known to be flaky'] = self.m.json.dumps(
              ignored_flakes, indent=2).split('/n')

    if new_failures:
      result.presentation.status = self.m.step.FAILURE
      self.m.tryserver.set_test_failure_tryjob_result()
    elif ignored_failures or ignored_flakes:
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
        test_suite.without_patch_failures_to_ignore())
    if not valid_results:
      self._invalid_test_results(test_suite)
      result = self.m.python.succeeding_step(
          '%s (test results summary)' % test_suite.name,
          ('\n%s (without patch) did not produce valid results, '
           'so no failures can safely be ignored') % test_suite.name)
      result.presentation.status = self.m.step.FAILURE
      self.m.tryserver.set_test_failure_tryjob_result()
      return False

    valid_results, failures = test_suite.with_patch_failures_including_retry()
    assert valid_results, (
        "If there were no valid results, then there was no "
        "point in running 'without patch'. This is a recipe bug.")
    new_failures = failures - ignored_failures

    return self._summarize_new_and_ignored_failures(
        test_suite, new_failures, ignored_failures,
        test_suite.get_summary_of_known_flaky_failures(),
        self.NEW_FAILURES_TEXT, self.IGNORED_FAILURES_TEXT,
        self.IGNORED_FLAKES_TEXT)

  def summarize_failing_test_with_no_retries(self, caller_api, test_suite):
    """Summarizes a failing test suite that is not going to be retried."""
    valid_results, new_failures = (
        test_suite.with_patch_failures_including_retry())

    if not valid_results:  # pragma: nocover
      self.m.python.infra_failing_step(
          '{} assertion'.format(test_suite.name),
          'This line should never be reached. If a test has invalid results '
          'and is not going to be retried, then a failing step should have '
          'already been emitted.')

    return self._summarize_new_and_ignored_failures(
        test_suite,
        new_failures,
        set(),
        test_suite.get_summary_of_known_flaky_failures(),
        new_failures_text=self.NEW_FAILURES_TEXT,
        ignored_failures_text=self.IGNORED_FAILURES_TEXT,
        ignored_flakes_text=self.IGNORED_FLAKES_TEXT)

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
    valid_results = test_suite.has_valid_results('with patch')
    valid_retry_shards_results = test_suite.has_valid_results(
        'retry shards with patch')
    if not (valid_results or valid_retry_shards_results):
      return set()

    suffix = 'with patch' if valid_results else 'retry shards with patch'
    with_patch_failures = set(test_suite.deterministic_failures(suffix))

    # FindIt wants to ignore failures that have status UNKNOWN/NOTRUN. This
    # logic will eventually live in FindIt, but for now, is implemented here.
    not_run = test_suite.findit_notrun(suffix)
    with_patch_failures = with_patch_failures - not_run

    # To reduce false positives, FindIt only wants tests to be marked as
    # potentially flaky if the the test passed in 'without patch'.
    valid_results, ignored_failures = (
        test_suite.without_patch_failures_to_ignore())

    return with_patch_failures - (ignored_failures if valid_results else set())

  def summarize_findit_flakiness(self, caller_api, test_suites):
    """Exports a summary of flakiness for post-processing by FindIt.

    There are several types of test flakiness. FindIt categories these by the
    layer at which the flakiness is discovered. One of these categories is for a
    test that fails, but when retried in a separate step, succeeds. This
    currently applies to 'retry shards with patch'. These are labeled 'Step
    Layer Flakiness'.

    'Step Layer Flakiness' doesn't include failures that are already known to be
    flaky on tip of tree, but FindIt still would like to know them, so they're
    exposed and labeled separately as 'Step Layer Skipped Known Flakiness'.

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
    step_layer_skipped_known_flakiness = {}
    for test_suite in test_suites:
      potential_test_flakes = self._findit_potential_test_flakes(
          caller_api, test_suite)

      known_flaky_failures = (
          potential_test_flakes & test_suite.known_flaky_failures)
      if known_flaky_failures:
        step_name = test_suite.name_of_step_for_suffix('with patch')
        step_layer_skipped_known_flakiness[step_name] = sorted(
            known_flaky_failures)

      # We only want to consider tests that failed in 'with patch' but succeeded
      # when retried by 'retry shards with patch' and that they're not known
      # flaky tests on tip of tree. If a test didn't run in either of these
      # steps, then we ignore it.
      valid_retry_shards_results, retry_shards_successes, _ = (
          test_suite.shard_retry_with_patch_results())
      if not valid_retry_shards_results:
        continue

      flaky_tests = (
          potential_test_flakes &
          retry_shards_successes - test_suite.known_flaky_failures)
      if flaky_tests:
        step_name = test_suite.name_of_step_for_suffix('with patch')
        step_layer_flakiness[step_name] = sorted(flaky_tests)

    potential_build_flakiness = {}
    for test_suite in test_suites:
      potential_test_flakes = self._findit_potential_test_flakes(
          caller_api, test_suite)

      valid_retry_shards_results, retry_shards_successes, _ = (
          test_suite.shard_retry_with_patch_results())
      if valid_retry_shards_results:
        potential_test_flakes = (potential_test_flakes - retry_shards_successes)

      potential_test_flakes = (
          potential_test_flakes - test_suite.known_flaky_failures)
      if potential_test_flakes:
        step_name = test_suite.name_of_step_for_suffix('with patch')
        potential_build_flakiness[step_name] = sorted(potential_test_flakes)

    # TODO(crbug.com/939063): Surface information about retried shards.
    if (step_layer_flakiness or step_layer_skipped_known_flakiness or
        potential_build_flakiness):
      output = {
          'Step Layer Flakiness':
              step_layer_flakiness,
          'Step Layer Skipped Known Flakiness':
              step_layer_skipped_known_flakiness,
          'Failing With Patch Tests That Caused Build Failure':
              potential_build_flakiness,
      }
      step = caller_api.python.succeeding_step(
          'FindIt Flakiness', 'Metadata for FindIt post processing.')
      step.presentation.logs['step_metadata'] = (json.dumps(
          output, sort_keys=True, indent=2)).splitlines()

  def _archive_test_results_summary(self, test_results_summary, dest_filename):
    """Archives the test results summary as JSON, storing it alongside the
    results from the first run."""
    script = self.m.chromium.repo_resource(
        'scripts', 'slave', 'chromium',
        'archive_layout_test_results_summary.py')
    args = [
        '--test-results-summary-json',
        self.m.json.input(test_results_summary), '--build-number',
        self.m.buildbucket.build.number, '--builder-name',
        self.m.buildbucket.builder_name, '--gs-bucket',
        'gs://chromium-layout-test-archives', '--dest-filename', dest_filename
    ]
    args += self.m.build.slave_utils_args
    self.m.build.python('archive_test_results_summary', script, args)

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

  def __init__(self, test_suites):
    self._test_suites = test_suites

  def pre_run(self, caller_api, suffix):  # pragma: no cover
    """Executes the |pre_run| method of each test.

    Args:
      caller_api - The api object given by the caller of this module.
      suffix - The test name suffix.
    """
    raise NotImplementedError()

  def run(self, caller_api, suffix):  # pragma: no cover
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

  def __init__(self, test_suites):
    super(LocalGroup, self).__init__(test_suites)

  def pre_run(self, caller_api, suffix):
    """Executes the |pre_run| method of each test."""
    for t in self._test_suites:
      self._run_func(t, t.pre_run, caller_api, suffix, False)

  def run(self, caller_api, suffix):
    """Executes the |run| method of each test."""
    for t in self._test_suites:
      self._run_func(t, t.run, caller_api, suffix, True)


class SwarmingGroup(TestGroup):

  def __init__(self, test_suites):
    super(SwarmingGroup, self).__init__(test_suites)
    self._task_ids_to_test = {}

  def pre_run(self, caller_api, suffix):
    """Executes the |pre_run| method of each test."""
    for t in self._test_suites:
      t.pre_run(caller_api, suffix)
      task = t.get_task(suffix)

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

        test.run(caller_api, suffix)
        del self._task_ids_to_test[key]
        break

      finished_sets, attempts = (
          caller_api.chromium_swarming.wait_for_finished_task_set(
              list(self._task_ids_to_test),
              suffix=((' (%s)' % suffix) if suffix else ''),
              attempts=attempts))
      for task_set in finished_sets:
        test = self._task_ids_to_test[tuple(task_set)]
        test.run(caller_api, suffix)
        del self._task_ids_to_test[task_set]

    # Testing this suite is hard, because the step_test_data for get_states
    # means that it's hard to force it to never return COMPLETED for tasks. This
    # shouldn't happen anyways, so hopefully not testing this will be fine.
    if self._task_ids_to_test:  # pragma: no cover
      # Something weird is going on, just collect tasks like normal, and log a
      # warning.
      result = caller_api.python.succeeding_step(
          'swarming tasks.get_states issue',
          ('swarming tasks.get_states seemed to indicate that all tasks for'
           ' this build were finished collecting, but the recipe thinks the'
           ' following tests still need to be collected:\n%s\nSomething is'
           ' probably wrong with the swarming server. Falling back on the old'
           ' collection logic.' % ', '.join(
               test.name for test in self._task_ids_to_test.values())))
      result.presentation.status = caller_api.step.WARNING

      for test in self._task_ids_to_test.values():
        # We won't collect any already collected tasks, as they're removed from
        # self._task_ids_to_test
        test.run(caller_api, suffix)
