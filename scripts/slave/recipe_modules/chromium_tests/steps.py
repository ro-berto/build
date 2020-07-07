# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import contextlib
import copy
import datetime
import hashlib
import json
import re
import string
import struct
import urlparse

from recipe_engine import recipe_api
from recipe_engine.types import freeze


RESULTS_URL = 'https://chromeperf.appspot.com'

# When we retry failing tests, we try to choose a high repeat count so that
# flaky tests will produce both failures and successes. The tradeoff is with
# total run time, which we want to keep low.
REPEAT_COUNT_FOR_FAILING_TESTS = 10

# Pinned version of
# https://chromium.googlesource.com/infra/infra/+/master/go/src/infra/cmd/mac_toolchain
MAC_TOOLCHAIN_PACKAGE = 'infra/tools/mac_toolchain/${platform}'
MAC_TOOLCHAIN_VERSION = (
    'git_revision:796d2b92cff93fc2059623ce0a66284373ceea0a')
MAC_TOOLCHAIN_ROOT    = '.'

# CIPD package containing various static test utilities and binaries for WPR
# testing.  Used with WprProxySimulatorTestRunner.
WPR_TOOLS_PACKAGE = 'chromium/ios/autofill/wpr-ios-tools'
WPR_TOOLS_VERSION = 'version:1.0'
WPR_TOOLS_ROOT = 'wpr-ios-tools'
WPR_REPLAY_DATA_ROOT = 'wpr-replay-data'

# Mapping of common names of supported iOS devices to product types
# exposed by the Swarming server.
IOS_PRODUCT_TYPES = {
    'iPad 4 GSM CDMA': 'iPad3,6',
    'iPad 5th Gen': 'iPad6,11',
    'iPad 6th Gen': 'iPad7,5',
    'iPad 7th Gen': 'iPad7,11',
    'iPad Air': 'iPad4,1',
    'iPad Air 2': 'iPad5,3',
    'iPhone 5': 'iPhone5,1',
    'iPhone 5s': 'iPhone6,1',
    'iPhone 6s': 'iPhone8,1',
    'iPhone 7': 'iPhone9,1',
    'iPhone X': 'iPhone10,3',
    'iPhone 11': 'iPhone12,1',
}

class TestOptions(object):
  """Abstracts command line flags to be passed to the test."""
  def __init__(self, repeat_count=None, test_filter=None, run_disabled=False,
               retry_limit=None):
    """Construct a TestOptions object with immutable attributes.

    Args:
      repeat_count - how many times to run each test
      test_filter - a list of tests, e.g.
                       ['suite11.test1',
                        'suite12.test2']
      run_disabled - whether to run tests that have been disabled.
      retry_limit - how many times to retry a test until getting a pass.
     """
    self._test_filter = freeze(test_filter)
    self._repeat_count = repeat_count
    self._run_disabled = run_disabled
    self._retry_limit = retry_limit

    # When this is true, the test suite should run all tests independently, with
    # no state leaked between them. This can significantly increase the time it
    # takes to run the tests.
    self._force_independent_tests = False

  @property
  def repeat_count(self):
    return self._repeat_count

  @property
  def run_disabled(self):
    return self._run_disabled

  @property
  def retry_limit(self):
    return self._retry_limit

  @property
  def test_filter(self):
    return self._test_filter


def _merge_arg(args, flag, value):
  args = [a for a in args if not a.startswith(flag)]
  if value is not None:
    return args + ['%s=%s' % (flag, str(value))]
  else:
    return args + [flag]


def _merge_args_and_test_options(test, args, options):
  """Adds args from test options.

  Args:
    test: A test suite. An instance of a subclass of Test.
    args: The list of args of extend.
    options: The TestOptions to use to extend args.

  Returns:
    The extended list of args.
  """
  args = args[:]

  if not (isinstance(test, (SwarmingGTestTest, LocalGTestTest)) or
          (isinstance(test,
                      (SwarmingIsolatedScriptTest, LocalIsolatedScriptTest)) and
           'blink_web_tests' in test.target_name)):
    # The args that are being merged by this function are only supported
    # by gtest and blink_web_tests.
    return args

  if options.test_filter:
    args = _merge_arg(args, '--gtest_filter', ':'.join(options.test_filter))
  if options.repeat_count and options.repeat_count > 1:
    args = _merge_arg(args, '--gtest_repeat', options.repeat_count)
  if options.retry_limit is not None:
    args = _merge_arg(args, '--test-launcher-retry-limit', options.retry_limit)
  if options.run_disabled:
    args = _merge_arg(args, '--gtest_also_run_disabled_tests', value=None)
  if options._force_independent_tests:
    if isinstance(test, (SwarmingGTestTest, LocalGTestTest)):
      args = _merge_arg(args, '--test-launcher-batch-limit', 1)
  return args


def _test_options_for_running(test_options, suffix, tests_to_retry):
  """Modifes a Test's TestOptions for a given suffix.

  When retrying tests without patch, we want to run the tests a fixed number of
  times, regardless of whether they succeed, to see if they flakily fail. Some
  recipes specify an explicit repeat_count -- for those, we don't override their
  desired behavior.

  Args:
    test_options: The test's initial TestOptions.
    suffix: A string suffix.
    tests_to_retry: A container of tests to retry.

  Returns:
    A copy of the initial TestOptions, possibly modified to support the suffix.

  """
  # We make a copy of test_options since the initial reference is persistent
  # across different suffixes.
  test_options_copy = copy.deepcopy(test_options)

  # If there are too many tests, avoid setting a repeat count since that can
  # cause timeouts. tests_to_retry can be None to indicate that all tests should
  # be run. It can also rarely be the empty list, which is caused by an infra
  # failure even though results are valid and all tests passed.
  # https://crbug.com/910706.
  if not tests_to_retry or len(tests_to_retry) > 100:
    return test_options_copy

  if test_options_copy.repeat_count is None and suffix == 'without patch':
    test_options_copy._repeat_count = REPEAT_COUNT_FOR_FAILING_TESTS

    # If we're repeating the tests 10 times, then we want to set retry_limit=0.
    # The default retry_limit of 3 means that failing tests will be retried 40
    # times, which is not our intention.
    test_options_copy._retry_limit = 0

    # Since we're retrying a small number of tests, force them to be
    # independent. This increases run time but produces more reliable results.
    test_options_copy._force_independent_tests = True

  return test_options_copy


class Test(object):
  """
  Base class for a test suite that can be run locally or remotely.

  Tests consist of three components:
    * configuration
    * logic for how to run the test
    * results

  The logic for how to run a test should only depend on the configuration, and
  not on global state. For example, once a SwarmingTest has been configured,
  calling pre_run() or run() should work regardless of context.

  The only exception is for local tests that depend on file-system state. We do
  not want to add the complexity of a file-system cache to this class, so
  changes to the file-system can affect behavior of the test.

  As part of this contract, methods that access configuration or results should
  never take an "api" parameter; the configuration and results should be
  self-contained. Likewise, the logic for running tests must take an "api"
  parameter to access relevant recipe modules, but should not look up state from
  those modules; the state should already be stored in the configuration.
  """

  def __init__(self,
               name,
               target_name=None,
               full_test_target=None,
               test_id_prefix=None,
               waterfall_mastername=None,
               waterfall_buildername=None):
    """
    Args:
      name: Displayed name of the test.
      target_name: Ninja build target for the test, a key in
          //testing/buildbot/gn_isolate_map.pyl,
          e.g. "browser_tests".
      full_test_target: a fully qualified Ninja target, e.g.
        "//chrome/test:browser_tests".
      test_id_prefix: Test_id prefix used by ResultDB, e.g.
          "ninja://chrome/test:telemetry_gpu_integration_test/trace_test/".
      waterfall_mastername (str): Matching waterfall buildbot master name.
        This value would be different from trybot master name.
      waterfall_buildername (str): Matching waterfall buildbot builder name.
        This value would be different from trybot builder name.
    """
    super(Test, self).__init__()

    # Contains a set of flaky failures that are known to be flaky, along with
    # the according id of the monorail bug filed for the flaky test.
    # The set of flaky tests is supposed to be a subset of the deterministic
    # failures.
    self._known_flaky_failures_map = {}

    # Contains a record of deterministic failures, one for each suffix. Maps
    # suffix to a list of tests.
    # Must be updated using update_test_run().
    self._deterministic_failures = {}

    # Contains a record of test runs, one for each suffix. Maps suffix to a dict
    # with the keys 'valid', 'failures', and 'pass_fail_counts'.
    #   'valid': A Boolean indicating whether the test run was valid.
    #   'failures': An iterable of strings -- each the name of a test that
    #   failed.
    #   'total_tests_ran': How many tests this test suite executed. Ignores
    #   retries ('pass_fail_counts' deals with that). Used to determine how many
    #   shards to trigger when retrying tests.
    #   'pass_fail_counts': A dictionary that provides the number of passes and
    #   failures for each test. e.g.
    #     {
    #       'test3': { 'PASS_COUNT': 3, 'FAIL_COUNT': 2 }
    #     }
    #   'findit_notrun': A temporary field for FindIt. Lists tests for which
    #   every test run had result NOTRUN or UNKNOWN. The CATS team expects to
    #   move this logic back into FindIt in Q3 2019, after the test results
    #   datastore has been cleaned up. https://crbug.com/934599.
    # Must be updated using update_test_run()
    self._test_runs = {}

    self._waterfall_mastername = waterfall_mastername
    self._waterfall_buildername = waterfall_buildername
    self._test_options = TestOptions()

    self._name = name
    self._target_name = target_name
    self._full_test_target = full_test_target
    self._test_id_prefix = test_id_prefix

    # A map from suffix [e.g. 'with patch'] to the name of the recipe engine
    # step that was invoked in run(). This makes the assumption that run() only
    # emits a single recipe engine step, and that the recipe engine step is the
    # one that best represents the run of the tests. This is used by FindIt to
    # look up the failing step for a test suite from buildbucket.
    self._suffix_step_name_map = {}

  @property
  def set_up(self):
    return None

  @property
  def tear_down(self):
    return None

  @property
  def test_options(self):
    return self._test_options

  @test_options.setter
  def test_options(self, value):  # pragma: no cover
    raise NotImplementedError(
        'This test %s does not support test options objects yet' % type(self))

  @property
  def abort_on_failure(self):
    """If True, abort build when test fails."""
    return False

  @property
  def name(self):
    return self._name

  @property
  def target_name(self):
    return self._target_name or self._name

  @property
  def full_test_target(self):
    """A fully qualified Ninja target, e.g. "//chrome/test:browser_tests"."""
    return self._full_test_target

  @property
  def test_id_prefix(self):
    """Prefix of test_id in ResultDB. e.g.

    "ninja://chrome/test:telemetry_gpu_integration_test/trace_test/"
    """
    return self._test_id_prefix

  @property
  def canonical_name(self):
    """Canonical name of the test, no suffix attached."""
    return self.name

  @property
  def isolate_target(self):
    """Returns isolate target name. Defaults to name."""
    return self.target_name

  @property
  def is_gtest(self):
    return False

  @property
  def runs_on_swarming(self):
    return False

  @property
  def known_flaky_failures(self):
    """Return a set of tests that failed but known to be flaky at ToT."""
    return set(self._known_flaky_failures_map.keys())

  def get_summary_of_known_flaky_failures(self):
    """Returns a set of text to use to display in the test results summary."""
    return {
        '%s: crbug.com/%s' % (test_name, issue_id)
        for test_name, issue_id in self._known_flaky_failures_map.iteritems()
    }

  def add_known_flaky_failure(self, test_name, monorail_issue):
    """Add a known flaky failure on ToT along with the monorail issue id."""
    self._known_flaky_failures_map[test_name] = monorail_issue

  def compile_targets(self):
    """List of compile targets needed by this test."""
    raise NotImplementedError()  # pragma: no cover

  def pre_run(self, api, suffix):  # pragma: no cover
    """Steps to execute before running the test."""
    del api, suffix
    return []

  @recipe_api.composite_step
  def run(self, api, suffix):  # pragma: no cover
    """Run the test.

    Implementations of this method must populate
    self._suffix_step_name_map[suffix] with the name of the recipe engine step
    that best represents the work performed by this Test.

    suffix is 'with patch' or 'without patch'
    """
    raise NotImplementedError()

  def has_valid_results(self, suffix):  # pragma: no cover
    """
    Returns True if results (failures) are valid.

    This makes it possible to distinguish between the case of no failures
    and the test failing to even report its results in machine-readable
    format.
    """
    if suffix not in self._test_runs:
      return False

    return self._test_runs[suffix]['valid']

  def pass_fail_counts(self, suffix):
    """Returns a dictionary of pass and fail counts for each test."""
    return self._test_runs[suffix]['pass_fail_counts']

  def shards_to_retry_with(self, original_num_shards, num_tests_to_retry):
    """Calculates the number of shards to run when retrying this test.

    Args:
      original_num_shards: The number of shards used to run the test when it
                           first ran.
      num_tests_to_retry: The number of tests we're trying to retry.

    Returns:
      The number of shards to use when retrying tests that failed.

    Note that this assumes this test has run 'with patch', and knows how many
    tests ran in that case. It doesn't make sense to ask how this test should
    run when retried, if it hasn't run already.
    """
    with_patch_total = self._test_runs['with patch']['total_tests_ran']
    with_patch_retry_total = (
        self._test_runs['retry shards with patch']['total_tests_ran']
        if 'retry shards with patch' in self._test_runs else 0)
    total_tests_ran = max(with_patch_total, with_patch_retry_total)
    assert total_tests_ran, (
        "We cannot compute the total number of tests to re-run if no tests "
        "were run 'with patch'. Expected %s to contain key 'total_tests_ran', "
        "but it didn't" % (self._test_runs['with patch']))

    # We want to approximately match the previous shard load. Using only one
    # shard can lead to a single shard running many more tests than it
    # normally does. As the number of tests to retry approaches the total
    # number of total tests ran, we get closer to running with the same number
    # of shards as we originally were triggered with.
    # Note that this technically breaks when we're running a tryjob on a CL
    # which changes the number of tests to be run.
    # Clamp to be 1 < value < original_num_shards, so that we don't trigger too
    # many shards, or 0 shards.
    #
    # Since we repeat failing tests REPEAT_COUNT_FOR_FAILING_TESTS times, we
    # artificially inflate the number of shards by that factor, since we expect
    # tests to take that much longer to run.
    #
    # We never allow more than num_test_to_retry shards, since that would leave
    # shards doing nothing.
    return int(min(min(
        max(
            original_num_shards * REPEAT_COUNT_FOR_FAILING_TESTS *
                (float(num_tests_to_retry) / total_tests_ran),
            1),
        original_num_shards), num_tests_to_retry))

  def failures(self, suffix):
    """Return tests that failed at least once (list of strings)."""
    assert suffix in self._test_runs, (
        'There is no data for the test run suffix ({0}). This should never '
        'happen as all calls to failures() should first check that the data '
        'exists.'.format(suffix))

    return self._test_runs[suffix]['failures']

  def deterministic_failures(self, suffix):
    """Return tests that failed on every test run(list of strings)."""
    assert suffix in self._deterministic_failures, (
        'There is no data for the test run suffix ({0}). This should never '
        'happen as all calls to deterministic_failures() should first check '
        'that the data exists.'.format(suffix))
    return self._deterministic_failures[suffix]

  def update_test_run(self, api, suffix, test_run):
    self._test_runs[suffix] = test_run
    self._deterministic_failures[suffix] = (
        api.test_utils.canonical.deterministic_failures(
            self._test_runs[suffix]))

  def name_of_step_for_suffix(self, suffix):
    """Returns the name of the step most relevant to the given suffix run.

    Most Tests will run multiple recipe engine steps. The name of the most
    relevant step is stored in  self._suffix_step_name_map. This method returns
    that step.

    This method should only be called if the suffix is known to have run.

    Returns:
      step_name: The name of the step that best represents 'running' the test.

    Raises:
      KeyError if the name is not present for the given suffix.
    """
    return self._suffix_step_name_map[suffix]

  @property
  def uses_isolate(self):
    """Returns true if the test is run via an isolate."""
    return False

  @property
  def uses_local_devices(self):
    return False # pragma: no cover

  def step_name(self, suffix):
    """Helper to uniformly combine tests's name with a suffix.

    Note this step_name is not necessarily the same as the step_name in actual
    builds, since there could be post-processing on the step_name by other
    apis, like swarming (see api.chromium_swarming.get_step_name()).
    """
    if not suffix:
      return self.name
    return '%s (%s)' % (self.name, suffix)

  def step_metadata(self, suffix=None):
    data = {
        'waterfall_mastername': self._waterfall_mastername,
        'waterfall_buildername': self._waterfall_buildername,
        'canonical_step_name': self.canonical_name,
        'isolate_target_name': self.isolate_target,
    }
    if suffix is not None:
      data['patched'] = suffix in (
          'with patch', 'retry shards with patch')
    return data

  def with_patch_failures_including_retry(self):
    return self.failures_including_retry('with patch')

  def failures_including_retry(self, suffix):
    """Returns test failures after retries.

    This method only considers tests to be failures if every test run fails,
    if the test runner retried tests, they're still considered successes as long
    as they didn't cause step failures.

    It also considers retried shards and the known flaky tests on tip of tree
    when determining if a test failed, which is to say that a test is determined
    as a failure if and only if it succeeded neither original run or retry and
    is NOT known to be flaky on tip of tree.

    Returns: A tuple (valid_results, failures).
      valid_results: A Boolean indicating whether results are valid.
      failures: A set of strings. Only valid if valid_results is True.
    """
    original_run_valid = self.has_valid_results(suffix)
    if original_run_valid:
      failures = self.deterministic_failures(suffix)
    retry_suffix = 'retry shards'
    if suffix:
      retry_suffix = ' '.join([retry_suffix, suffix])
    retry_shards_valid = self.has_valid_results(retry_suffix)
    if retry_shards_valid:
      retry_shards_failures = self.deterministic_failures(
          retry_suffix)

    if original_run_valid and retry_shards_valid:
      # TODO(martiniss): Maybe change this behavior? This allows for failures
      # in 'retry shards with patch' which might not be reported to devs, which
      # may confuse them.
      return True, (
          set(failures).intersection(retry_shards_failures) -
          self.known_flaky_failures)

    if original_run_valid:
      return True, set(failures) - self.known_flaky_failures

    if retry_shards_valid:
      return True, set(retry_shards_failures) - self.known_flaky_failures

    return False, None

  # TODO(crbug.com/1040596): Remove this method and update callers to use
  # |deterministic_failures('with patch')| once the bug is fixed.
  #
  # Currently, the sematics of this method is only a subset of
  # |deterministic_failures('with patch')| due to that it's missing tests that
  # failed "with patch", but passed in "retry shards with patch".
  def has_failures_to_summarize(self):
    _, failures = self.failures_including_retry('with patch')
    return bool(failures or self.known_flaky_failures)

  def findit_notrun(self, suffix):
    """Returns tests that had status NOTRUN/UNKNOWN.

    FindIt has special logic for handling for tests with status NOTRUN/UNKNOWN.
    This method returns test for which every test run had a result of either
    NOTRUN or UNKNOWN.

    Returns:
      not_run_tests: A set of strings. Only valid if valid_results is True.
    """
    assert self.has_valid_results(suffix), (
        'findit_notrun must only be called when the test run is known to have '
        'valid results.')
    return self._test_runs[suffix]['findit_notrun']

  def without_patch_failures_to_ignore(self):
    """Returns test failures that should be ignored.

    Tests that fail in 'without patch' should be ignored, since they're failing
    without the CL patched in. If a test is flaky, it is treated as a failing
    test.

    Returns: A tuple (valid_results, failures_to_ignore).
      valid_results: A Boolean indicating whether failures_to_ignore is valid.
      failures_to_ignore: A set of strings. Only valid if valid_results is True.
    """
    if not self.has_valid_results('without patch'):
      return (False, None)

    pass_fail_counts = self.pass_fail_counts('without patch')
    ignored_failures = set()
    for test_name, results in pass_fail_counts.iteritems():
      # If a test fails at least once, then it's flaky on tip of tree and we
      # should ignore it.
      if results['fail_count'] > 0:
        ignored_failures.add(test_name)
    return (True, ignored_failures)

  def shard_retry_with_patch_results(self):
    """Returns passing and failing tests ran for retry shards with patch.

    Only considers tests to be failures if every test run fails. Flaky tests are
    considered successes as they don't fail a step.

    Returns: A tuple (valid_results, passing_tests).
      valid_results: A Boolean indicating whether results are present and valid.
      passing_tests: A set of strings. Only valid if valid_results is True.
      failing_tests: A set of strings. Only valid if valid_results is True.
    """
    suffix = 'retry shards with patch'
    if not self.has_valid_results(suffix):
      return (False, None, None)

    passing_tests = set()
    failing_tests = set()
    for test_name, result in (
        self.pass_fail_counts(suffix).iteritems()):
      if result['pass_count'] > 0:
        passing_tests.add(test_name)
      else:
        failing_tests.add(test_name)

    return (True, passing_tests, failing_tests)

  def _tests_to_retry(self, suffix):
    """Computes the tests to run on an invocation of the test suite.

    Args:
      suffix: A unique identifier for this test suite invocation. Must be 'with
      patch', 'retry shards with patch', or 'without patch'.

    Returns:
      A list of tests to retry. Returning None means all tests should be run.
    """
    # For the initial invocation, run every test in the test suite. Also run
    # every test when retrying shards, as we explicitly want to run every test
    # when retrying a shard.
    if suffix in ('with patch', 'retry shards with patch'):
      return None

    # For the second invocation, run previously deterministically failing tests.
    # When a patch is adding a new test (and it fails), the test runner is
    # required to just ignore the unknown test.
    if suffix == 'without patch':
      # Invalid results should be treated as if every test failed.
      valid_results, failures = self.with_patch_failures_including_retry()
      return sorted(failures -
                    self.known_flaky_failures) if valid_results else None

    # If we don't recognize the step, then return None. This makes it easy for
    # bugs to slip through, but this matches the previous behavior. Importantly,
    # all the tests fail to pass a suffix.
    return None


class TestWrapper(Test):  # pragma: no cover
  """ A base class for Tests that wrap other Tests.

  By default, all functionality defers to the wrapped Test.
  """

  def __init__(self, test, **kwargs):
    super(TestWrapper, self).__init__(test.name, **kwargs)
    self._test = test

  @property
  def set_up(self):
    return self._test.set_up

  @property
  def tear_down(self):
    return self._test.tear_down

  @property
  def test_options(self):
    return self._test.test_options

  @test_options.setter
  def test_options(self, value):
    self._test.test_options = value

  @property
  def abort_on_failure(self):
    return self._test.abort_on_failure

  @property
  def name(self):
    return self._test.name

  @property
  def isolate_target(self):
    return self._test.isolate_target

  def compile_targets(self):
    return self._test.compile_targets()

  def pre_run(self, api, suffix):
    return self._test.pre_run(api, suffix)

  @recipe_api.composite_step
  def run(self, api, suffix):
    return self._test.run(api, suffix)

  def has_valid_results(self, suffix):
    return self._test.has_valid_results(suffix)

  def failures(self, suffix):
    return self._test.failures(suffix)

  def deterministic_failures(self, suffix):
    return self._test.deterministic_failures(suffix)

  def findit_notrun(self, suffix):
    return self._test.findit_notrun(suffix)

  def pass_fail_counts(self, suffix):
    return self._test.pass_fail_counts(suffix)

  @property
  def uses_isolate(self):
    return self._test.uses_isolate

  @property
  def uses_local_devices(self):
    return self._test.uses_local_devices

  def step_metadata(self, suffix=None):
    return self._test.step_metadata(suffix=suffix)


class ExperimentalTest(TestWrapper):
  """A test wrapper that runs the wrapped test on an experimental test.

  Experimental tests:
    - can run at <= 100%, depending on the experiment_percentage.
    - will not cause the build to fail.
  """

  def __init__(self, test, experiment_percentage, api):
    super(ExperimentalTest, self).__init__(test)
    self._experiment_percentage = max(0, min(100, int(experiment_percentage)))
    self._is_in_experiment = self._calculate_is_in_experiment(api)

  def _experimental_suffix(self, suffix):
    if not suffix:
      return 'experimental'
    return '%s, experimental' % (suffix)

  def _calculate_is_in_experiment(self, api):
    # Arbitrarily determine whether to run the test based on its experiment
    # key. Tests with the same experiment key should always either be in the
    # experiment or not; i.e., given the same key, this should always either
    # return True or False, but not both.
    #
    # The experiment key is either:
    #   - builder name + patchset + name of the test, for trybots
    #   - builder name + build number + name of the test, for CI bots
    #
    # These keys:
    #   - ensure that the same experiment configuration is always used for
    #     a given patchset
    #   - allow independent variation of experiments on the same test
    #     across different builders
    #   - allow independent variation of experiments on different tests
    #     across a single build
    #
    # The overall algorithm is copied from the CQ's implementation of
    # experimental builders, albeit with different experiment keys.

    criteria = [
      api.buildbucket.builder_name,
      (api.tryserver.gerrit_change and api.tryserver.gerrit_change.change) or
        api.buildbucket.build.number or '0',
      self.name,
    ]

    digest = hashlib.sha1(''.join(str(c) for c in criteria)).digest()
    short = struct.unpack_from('<H', digest)[0]
    return self._experiment_percentage * 0xffff >= short * 100


  def _is_in_experiment_and_has_valid_results(self, suffix):
    return (self._is_in_experiment and
        super(ExperimentalTest, self).has_valid_results(
            self._experimental_suffix(suffix)))

  @property
  def abort_on_failure(self):
    return False

  #override
  def pre_run(self, api, suffix):
    if not self._is_in_experiment:
      return []

    try:
      return super(ExperimentalTest, self).pre_run(
          api, self._experimental_suffix(suffix))
    except api.step.StepFailure:
      pass

  #override
  @recipe_api.composite_step
  def run(self, api, suffix):
    if not self._is_in_experiment:
      return []

    try:
      return super(ExperimentalTest, self).run(
          api, self._experimental_suffix(suffix))
    except api.step.StepFailure:
      pass

  #override
  def has_valid_results(self, suffix):
    if self._is_in_experiment:
      # Call the wrapped test's implementation in case it has side effects,
      # but ignore the result.
      super(ExperimentalTest, self).has_valid_results(
          self._experimental_suffix(suffix))
    return True

  #override
  def failures(self, suffix):
    if self._is_in_experiment_and_has_valid_results(suffix):
      # Call the wrapped test's implementation in case it has side effects,
      # but ignore the result.
      super(ExperimentalTest, self).failures(self._experimental_suffix(suffix))
    return []

  #override
  def deterministic_failures(self, suffix):
    if self._is_in_experiment_and_has_valid_results(suffix):
      # Call the wrapped test's implementation in case it has side effects,
      # but ignore the result.
      super(ExperimentalTest, self).deterministic_failures(
          self._experimental_suffix(suffix))
    return []

  #override
  def findit_notrun(self, suffix): # pragma: no cover
    if self._is_in_experiment_and_has_valid_results(suffix):
      # Call the wrapped test's implementation in case it has side effects,
      # but ignore the result.
      super(ExperimentalTest, self).findit_notrun(
          self._experimental_suffix(suffix))
    return set()

  def pass_fail_counts(self, suffix):
    if self._is_in_experiment_and_has_valid_results(suffix):
      # Call the wrapped test's implementation in case it has side effects,
      # but ignore the result.
      super(ExperimentalTest, self).pass_fail_counts(
          self._experimental_suffix(suffix))
    return {}


class SizesStep(Test):
  def __init__(self, results_url, perf_id, **kwargs):
    super(SizesStep, self).__init__('sizes', **kwargs)
    self.results_url = results_url
    self.perf_id = perf_id

  @recipe_api.composite_step
  def run(self, api, suffix):
    step_result = api.chromium.sizes(self.results_url, self.perf_id)
    self._suffix_step_name_map[suffix] = '.'.join(step_result.name_tokens)
    return step_result

  def compile_targets(self):
    return ['chrome']

  def has_valid_results(self, suffix):
    # TODO(sebmarchand): implement this function as well as the
    # |failures| one.
    return True

  def failures(self, suffix):
    return []

  def deterministic_failures(self, suffix):
    return []

  def findit_notrun(self, suffix):
    return set()

  def pass_fail_counts(self, suffix): # pragma: no cover
    return {}


class ScriptTest(Test):  # pylint: disable=W0232
  """
  Test which uses logic from script inside chromium repo.

  This makes it possible to keep the logic src-side as opposed
  to the build repo most Chromium developers are unfamiliar with.

  Another advantage is being to test changes to these scripts
  on trybots.

  All new tests are strongly encouraged to use this infrastructure.
  """

  def __init__(self, name, script, all_compile_targets, script_args=None,
               override_compile_targets=None,
               waterfall_mastername=None, waterfall_buildername=None, **kwargs):
    super(ScriptTest, self).__init__(
        name, waterfall_mastername=waterfall_mastername,
        waterfall_buildername=waterfall_buildername, **kwargs)
    self._script = script
    self._all_compile_targets = all_compile_targets
    self._script_args = script_args
    self._override_compile_targets = override_compile_targets

  def compile_targets(self):
    if self._override_compile_targets:
      return self._override_compile_targets

    substitutions = {'name': self._name}

    if not self._script in self._all_compile_targets:
      return []

    return [string.Template(s).safe_substitute(substitutions)
            for s in self._all_compile_targets[self._script]]

  @recipe_api.composite_step
  def run(self, api, suffix):
    name = self.name
    if suffix:
      name += ' (%s)' % suffix  # pragma: no cover

    run_args = []

    tests_to_retry = self._tests_to_retry(suffix)
    if tests_to_retry:
      run_args.extend([
          '--filter-file', api.json.input(tests_to_retry)
      ])  # pragma: no cover

    try:
      script_args = []
      if self._script_args:
        script_args = ['--args', api.json.input(self._script_args)]
      api.python(
          name,
          # Enforce that all scripts are in the specified directory
          # for consistency.
          api.path['checkout'].join(
              'testing', 'scripts', api.path.basename(self._script)),
          args=(api.chromium_tests.get_common_args_for_scripts() +
                script_args +
                ['run', '--output', api.json.output()] +
                run_args),
          step_test_data=lambda: api.json.test_api.output(
              {'valid': True, 'failures': []}))
    finally:
      result = api.step.active_result
      self._suffix_step_name_map[suffix] = '.'.join(result.name_tokens)

      failures = None
      if result.json.output:
        failures = result.json.output.get('failures')
      if failures is None:
        self.update_test_run(
            api, suffix, api.test_utils.canonical.result_format())
        api.python.failing_step(
            '%s with suffix %s had an invalid result' % (self.name, suffix),
            'The recipe expected the result to contain the key \'failures\'.'
            ' Contents are:\n%s' % api.json.dumps(
                result.json.output, indent=2))

      # Most scripts do not emit 'successes'. If they start emitting
      # 'successes', then we can create a proper results dictionary.
      pass_fail_counts = {}
      for failing_test in failures:
        pass_fail_counts.setdefault(
            failing_test, {'pass_count': 0, 'fail_count': 0})
        pass_fail_counts[failing_test]['fail_count'] += 1

      # It looks like the contract we have with these tests doesn't expose how
      # many tests actually ran. Just say it's the number of failures for now,
      # this should be fine for these tests.
      self.update_test_run(
          api, suffix, {
          'failures': failures,
          'valid': result.json.output['valid'],
          'total_tests_ran': len(failures),
          'pass_fail_counts': pass_fail_counts,
          'findit_notrun': set(),
      })

      _, failures = api.test_utils.limit_failures(failures)
      result.presentation.step_text += (
          api.test_utils.format_step_text([
            ['failures:', failures]
          ]))


    return self._test_runs[suffix]


class LocalGTestTest(Test):

  def __init__(self,
               name,
               args=None,
               target_name=None,
               full_test_target=None,
               test_id_prefix=None,
               revision=None,
               webkit_revision=None,
               android_shard_timeout=None,
               override_compile_targets=None,
               commit_position_property='got_revision_cp',
               use_xvfb=True,
               waterfall_mastername=None,
               waterfall_buildername=None,
               set_up=None,
               tear_down=None,
               **runtest_kwargs):
    """Constructs an instance of LocalGTestTest.

    Args:
      name: Displayed name of the test. May be modified by suffixes.
      args: Arguments to be passed to the test.
      target_name: Actual name of the test. Defaults to name.
      full_test_target: a fully qualified Ninja target, e.g.
        "//chrome/test:browser_tests".
      test_id_prefix: Test_id prefix used by ResultDB, e.g.
          "ninja://chrome/test:telemetry_gpu_integration_test/trace_test/".
      revision: Revision of the Chrome checkout.
      webkit_revision: Revision of the WebKit checkout.
      override_compile_targets: List of compile targets for this test
          (for tests that don't follow target naming conventions).
      commit_position_property: Property to get Chromium's commit position.
          Defaults to 'got_revision_cp'.
      use_xvfb: whether to use the X virtual frame buffer. Only has an
          effect on Linux. Defaults to True. Mostly harmless to
          specify this, except on GPU bots.
      set_up: Optional setup scripts.
      tear_down: Optional teardown script.
      runtest_kwargs: Additional keyword args forwarded to the runtest.


    """
    super(LocalGTestTest, self).__init__(
        name,
        target_name=target_name,
        full_test_target=full_test_target,
        test_id_prefix=test_id_prefix,
        waterfall_mastername=waterfall_mastername,
        waterfall_buildername=waterfall_buildername)
    self._args = args or []
    self._target_name = target_name
    self._revision = revision
    self._webkit_revision = webkit_revision
    self._android_shard_timeout = android_shard_timeout
    self._override_compile_targets = override_compile_targets
    self._commit_position_property = commit_position_property
    self._use_xvfb = use_xvfb
    # FIXME: This should be a named argument, rather than catching all keyword
    # arguments to this constructor.
    self._runtest_kwargs = runtest_kwargs
    self._gtest_results = {}
    self._set_up = set_up
    self._tear_down = tear_down

  @Test.test_options.setter
  def test_options(self, value):
    self._test_options = value

  @property
  def set_up(self):
    return self._set_up

  @property
  def tear_down(self):
    return self._tear_down

  @property
  def uses_local_devices(self):
    return True  # pragma: no cover

  @property
  def is_gtest(self):
    return True

  def compile_targets(self):
    # TODO(phajdan.jr): clean up override_compile_targets (remove or cover).
    if self._override_compile_targets:  # pragma: no cover
      return self._override_compile_targets
    return [self.target_name]

  @recipe_api.composite_step
  def run(self, api, suffix):
    is_android = api.chromium.c.TARGET_PLATFORM == 'android'
    is_fuchsia = api.chromium.c.TARGET_PLATFORM == 'fuchsia'

    tests_to_retry = self._tests_to_retry(suffix)
    test_options = _test_options_for_running(self.test_options,
                                             suffix, tests_to_retry)
    args = _merge_args_and_test_options(self, self._args, test_options)

    if tests_to_retry:
      args = _merge_arg(args, '--gtest_filter', ':'.join(tests_to_retry))

    gtest_results_file = api.test_utils.gtest_results(add_json_log=False)

    step_test_data = lambda: api.test_utils.test_api.canned_gtest_output(True)

    kwargs = {
      'name': self.step_name(suffix),
      'args': args,
      'step_test_data': step_test_data,
    }
    if is_android:
      kwargs['json_results_file'] = gtest_results_file
      kwargs['shard_timeout'] = self._android_shard_timeout
    else:
      kwargs['xvfb'] = self._use_xvfb
      kwargs['test_type'] = self.name
      kwargs['annotate'] = 'gtest'
      kwargs['test_launcher_summary_output'] = gtest_results_file
      kwargs.update(self._runtest_kwargs)

    try:
      if is_android:
        api.chromium_android.run_test_suite(self.target_name, **kwargs)
      elif is_fuchsia:
        script = api.chromium.output_dir.join('bin',
                                              'run_%s' % self.target_name)
        args.extend(['--test-launcher-summary-output', gtest_results_file])
        args.extend(['--system-log-file', '${ISOLATED_OUTDIR}/system_log'])
        api.python(self.target_name, script, args)
      else:
        api.chromium.runtest(self.target_name, revision=self._revision,
                             webkit_revision=self._webkit_revision,
                             **kwargs)
      # TODO(kbr): add functionality to generate_gtest to be able to
      # force running these local gtests via isolate from the src-side
      # JSON files. crbug.com/584469
    finally:
      step_result = api.step.active_result
      self._suffix_step_name_map[suffix] = '.'.join(step_result.name_tokens)
      if not hasattr(step_result, 'test_utils'): # pragma: no cover
        self.update_test_run(
            api, suffix, api.test_utils.canonical.result_format())
      else:
        gtest_results = step_result.test_utils.gtest_results
        self.update_test_run(
            api, suffix, gtest_results.canonical_result_format())

      r = api.test_utils.present_gtest_failures(step_result)
      if r:
        self._gtest_results[suffix] = r

        api.test_results.upload(
            api.json.input(r.raw),
            test_type=self.name,
            chrome_revision=api.bot_update.last_returned_properties.get(
                self._commit_position_property, 'refs/x@{#0}'))

    return step_result

  def pass_fail_counts(self, suffix):
    if self._gtest_results.get(suffix):
      # test_result exists and is not None.
      return self._gtest_results[suffix].pass_fail_counts
    return {}


class ResultsHandler(object):

  def upload_results(self, api, results, step_name, passed,
                     step_suffix=None):  # pragma: no cover
    """Uploads test results to the Test Results Server.

    Args:
      api: Recipe API object.
      results: Results returned by the step.
      step_name: Name of the step that produced results.
      passed: If the test being uploaded passed during execution.
      step_suffix: Suffix appended to the step name.
    """
    raise NotImplementedError()

  def render_results(self, api, results, presentation): # pragma: no cover
    """Renders the test result into the step's output presentation.

    Args:
      api: Recipe API object.
      results: A TestResults object.
      presentation: Presentation output of the step.
    """
    raise NotImplementedError()

  def validate_results(self, api, results):  # pragma: no cover
    """Validates test results and returns a list of failures.

    Args:
      api: Recipe API object.
      results: Results returned by the step.

    Returns:
      (valid, failures, pass_fail_counts), where valid is True when results are
      valid, and failures is a list of strings (typically names of failed
      tests). pass_fail_counts is a dictionary that gives the number of passes
      and fails for each test.
    """
    raise NotImplementedError()


class JSONResultsHandler(ResultsHandler):
  MAX_FAILS = 30

  def __init__(self, ignore_task_failure=False):
    self._ignore_task_failure = ignore_task_failure

  @classmethod
  def _format_failures(cls, state, failures):
    """Format a human-readable explanation of what has failed.

    Args:
      state: A string describing what type of failure it was.
      failures: a dictionary mapping test names to failure information.
        The failure information could be empty or it could be a dictionary
        of per-test fields per
        https://chromium.googlesource.com/chromium/src/+/master/docs/testing/json_test_results_format.md

    Returns:
      A tuple: (failure state, list of failure strings).
    """
    index = 0
    failure_strings = []
    num_failures = len(failures)

    for test_name in sorted(failures):
      if index >= cls.MAX_FAILS:
        failure_strings.append('* ... %d more (%d total) ...' % (
            num_failures - cls.MAX_FAILS, num_failures))
        break
      if failures[test_name] and 'shard' in failures[test_name]:
        shard = failures[test_name]['shard']
        failure_strings.append('* {test} (shard #{shard})'.format(
            test=test_name, shard=shard))
      else:
        failure_strings.append('* {test}'.format(test=test_name))
      index += 1

    return ('{state}:'.format(state=state), failure_strings)

  # TODO(tansell): Make this better formatted when milo supports html rendering.
  @classmethod
  def _format_counts(cls, state, expected, unexpected, highlight=False):
    hi_left = ''
    hi_right = ''
    if highlight and unexpected > 0:
      hi_left = '>>>'
      hi_right = '<<<'
    return (
        "* %(state)s: %(total)d (%(expected)d expected, "
        "%(hi_left)s%(unexpected)d unexpected%(hi_right)s)") % dict(
            state=state, total=expected+unexpected,
            expected=expected, unexpected=unexpected,
            hi_left=hi_left, hi_right=hi_right)

  def upload_results(self, api, results, step_name, passed, step_suffix=None):
    if hasattr(results, 'as_jsonish'):
      results = results.as_jsonish()

    # Only version 3 of results is supported by the upload server.
    if not results or results.get('version', None) != 3:
      return

    chrome_revision_cp = api.bot_update.last_returned_properties.get(
        'got_revision_cp', 'refs/x@{#0}')

    _, chrome_revision = api.commit_position.parse(str(chrome_revision_cp))
    chrome_revision = str(chrome_revision)
    api.test_results.upload(
      api.json.input(results), chrome_revision=chrome_revision,
      test_type=step_name)

  def render_results(self, api, results, presentation):
    failure_status = (
        api.step.WARNING if self._ignore_task_failure else api.step.FAILURE)

    if not results.valid:
      presentation.status = api.step.EXCEPTION
      presentation.step_text = api.test_utils.INVALID_RESULTS_MAGIC
      return

    step_text = []

    if results.total_test_runs == 0:
      step_text += [
          ('Total tests: n/a',),
      ]

    # TODO(tansell): https://crbug.com/704066 - Kill simplified JSON format.
    elif results.version == 'simplified':
      if results.unexpected_failures:
        presentation.status = failure_status

      step_text += [
          ('%s passed, %s failed (%s total)' % (
              len(results.passes.keys()),
              len(results.unexpected_failures.keys()),
              len(results.tests)),),
      ]

    else:
      if results.unexpected_flakes:
        presentation.status = api.step.WARNING
      if results.unexpected_failures or results.unexpected_skipped:
        presentation.status = (
            api.step.WARNING if self._ignore_task_failure else api.step.FAILURE)

      step_text += [
          ('Total tests: %s' % len(results.tests), [
              self._format_counts(
                  'Passed',
                  len(results.passes.keys()),
                  len(results.unexpected_passes.keys())),
              self._format_counts(
                  'Skipped',
                  len(results.skipped.keys()),
                  len(results.unexpected_skipped.keys())),
              self._format_counts(
                  'Failed',
                  len(results.failures.keys()),
                  len(results.unexpected_failures.keys()),
                  highlight=True),
              self._format_counts(
                  'Flaky',
                  len(results.flakes.keys()),
                  len(results.unexpected_flakes.keys()),
                  highlight=True),
              ]
          ),
      ]

    # format_step_text will automatically trim these if the list is empty.
    step_text += [
        self._format_failures(
            'Unexpected Failures', results.unexpected_failures),
    ]
    step_text += [
        self._format_failures(
            'Unexpected Flakes', results.unexpected_flakes),
    ]
    step_text += [
        self._format_failures(
            'Unexpected Skips', results.unexpected_skipped),
    ]

    # Unknown test results mean something has probably gone wrong, mark as an
    # exception.
    if results.unknown:
      presentation.status = api.step.EXCEPTION
    step_text += [
        self._format_failures(
            'Unknown test result', results.unknown),
    ]

    presentation.step_text += api.test_utils.format_step_text(step_text)

    # Handle any artifacts that the test produced if necessary.
    self._add_links_to_artifacts(api, results, presentation)

  def validate_results(self, api, results):
    test_results = api.test_utils.create_results_from_json(results)
    return test_results.canonical_result_format()

  def _add_links_to_artifacts(self, api, results, presentation):
    del api
    # Add any links to artifacts that are already available.
    # TODO(https://crbug.com/980274): Either handle the case of artifacts whose
    # paths are filepaths, or add the ability for merge scripts to upload
    # artifacts to a storage bucket and update the path to the URL before
    # getting to this point.
    if not results.valid or results.version == 'simplified':
      return
    artifacts = self._find_artifacts(results.raw)

    # We don't want to flood Milo with links if a bunch of artifacts are
    # generated, so put a cap on the number we're willing to show.
    max_links = 15
    num_links = 0
    for artifact_map in artifacts.values():
      for artifact_paths in artifact_map.values():
        num_links += len(artifact_paths)

    bulk_log = []
    for test_name, test_artifacts in artifacts.items():
      for artifact_type, artifact_paths in test_artifacts.items():
        for path in artifact_paths:
          link_title = '%s produced by %s' % (artifact_type, test_name)
          if num_links < max_links:
            presentation.links[link_title] = path
          else:
            bulk_log.append('%s: %s' % (link_title, path))
    if bulk_log:
      log_title = (
          'Too many artifacts produced to link individually, click for links')
      presentation.logs[log_title] = bulk_log

  def _find_artifacts(self, raw_results):
    """Finds artifacts in the given JSON results.

    Currently, only finds artifacts whose paths are HTTPS URLs, see
    https://crbug.com/980274 for more details.

    Returns:
      A dict of full test names to dicts of artifact types to paths.
    """
    tests = raw_results.get('tests', {})
    path_delimiter = raw_results.get('path_delimiter', '.')
    return self._recurse_artifacts(tests, '', path_delimiter)

  def _recurse_artifacts(self, sub_results, name_so_far, path_delimiter):
    is_leaf_node = 'actual' in sub_results and 'expected' in sub_results
    if is_leaf_node:
      if 'artifacts' not in sub_results:
        return {}
      url_artifacts = {}
      for artifact_type, artifact_paths in sub_results['artifacts'].items():
        for artifact_path in artifact_paths:
          parse_result = urlparse.urlparse(artifact_path)
          if parse_result.scheme == 'https' and parse_result.netloc:
            url_artifacts.setdefault(artifact_type, []).append(artifact_path)
      return {name_so_far: url_artifacts} if url_artifacts else {}

    artifacts = {}
    for key, val in sub_results.items():
      if isinstance(val, (dict, collections.OrderedDict)):
        updated_name = name_so_far + path_delimiter + str(key)
        # Strip off the leading delimiter if this is the first iteration
        if not name_so_far:
          updated_name = updated_name[1:]
        artifacts.update(
            self._recurse_artifacts(val, updated_name, path_delimiter))
    return artifacts


class FakeCustomResultsHandler(ResultsHandler):
  """Result handler just used for testing."""

  def validate_results(self, api, results):
    invalid_dictionary = api.test_utils.canonical.result_format()
    invalid_dictionary['valid'] = True
    return invalid_dictionary

  def render_results(self, api, results, presentation):
    presentation.step_text += api.test_utils.format_step_text([
        ['Fake results data',[]],
    ])
    presentation.links['uploaded'] = 'fake://'

  def upload_results(self, api, results, step_name, passed, step_suffix=None):
    api.test_utils.create_results_from_json(results)


def _clean_step_name(step_name, suffix):
  """
  Based on
  https://crrev.com/48baea8de14f5a17aef2edd7d0b8c00d7bbf7909/go/src/infra/appengine/test-results/frontend/builders.go#260
  Some tests add 'suffixes' in addition to the regular suffix, in order to
  distinguish different runs of the same test suite on different hardware. We
  don't want this to happen for layout test result uploads, since we have no
  easy way to discover this new name. So, we normalize the step name before
  uploading results.
  """
  if ' ' in step_name:
    step_name = step_name.split(' ')[0]

  if not suffix:
    return step_name

  return '%s (%s)' % (step_name, suffix)

class LayoutTestResultsHandler(JSONResultsHandler):
  """Uploads layout test results to Google storage."""

  def upload_results(self, api, results, step_name, passed, step_suffix=None):
    # Also upload to standard JSON results handler
    JSONResultsHandler.upload_results(self, api, results, step_name, passed,
                                      step_suffix)

    # LayoutTest's special archive and upload results
    results_dir = api.path['start_dir'].join('layout-test-results')

    buildername = api.buildbucket.builder_name
    buildnumber = api.buildbucket.build.number

    archive_layout_test_results = api.chromium.repo_resource(
        'scripts', 'slave', 'chromium', 'archive_layout_test_results.py')

    archive_layout_test_args = [
      '--results-dir', results_dir,
      '--build-dir', api.chromium.c.build_dir,
      '--build-number', buildnumber,
      '--builder-name', buildername,
      '--gs-bucket', 'gs://chromium-layout-test-archives',
      '--staging-dir', api.path['cache'].join('chrome_staging'),
    ]
    if not api.tryserver.is_tryserver:
      archive_layout_test_args.append('--store-latest')

    # TODO: The naming of the archive step is clunky, but the step should
    # really be triggered src-side as part of the post-collect merge and
    # upload, and so this should go away when we make that change.
    step_name = _clean_step_name(step_name, step_suffix)
    archive_layout_test_args += ['--step-name', step_name]
    archive_step_name = 'archive results for ' + step_name

    archive_layout_test_args += api.build.slave_utils_args
    # TODO(phajdan.jr): Pass gs_acl as a parameter, not build property.
    if api.properties.get('gs_acl'):
      archive_layout_test_args.extend(['--gs-acl', api.properties['gs_acl']])
    archive_result = api.build.python(
      archive_step_name,
      archive_layout_test_results,
      archive_layout_test_args)

    # TODO(tansell): Move this to render_results function
    sanitized_buildername = re.sub('[ .()]', '_', buildername)
    base = (
      "https://test-results.appspot.com/data/layout_results/%s/%s"
      % (sanitized_buildername, buildnumber))
    base += '/' + step_name

    archive_result.presentation.links['layout_test_results'] = (
        base + '/layout-test-results/results.html')
    archive_result.presentation.links['(zip)'] = (
        base + '/layout-test-results.zip')
    if not passed:
      # This makes sure that the step shows up when people select 'non-green'
      # on the Milo UI.
      archive_result.presentation.status = api.step.FAILURE
      archive_result.presentation.step_text = (
          "Step is marked red because the test itself failed. This is done so"
          " the step shows up in the \"Non-Green\" step filter in the UI.")


class SwarmingTest(Test):
  # Some suffixes should have marginally higher priority. See crbug.com/937151.
  SUFFIXES_TO_INCREASE_PRIORITY = [
      'without patch', 'retry shards with patch' ]

  def __init__(self,
               name,
               dimensions=None,
               target_name=None,
               full_test_target=None,
               test_id_prefix=None,
               extra_suffix=None,
               expiration=None,
               hard_timeout=None,
               io_timeout=None,
               waterfall_mastername=None,
               waterfall_buildername=None,
               set_up=None,
               tear_down=None,
               optional_dimensions=None,
               service_account=None,
               isolate_coverage_data=None,
               isolate_profile_data=None,
               merge=None,
               ignore_task_failure=None,
               containment_type=None,
               idempotent=None,
               shards=1,
               cipd_packages=None,
               named_caches=None,
               **kwargs):
    """Constructs an instance of SwarmingTest.

    Args:
      name: Displayed name of the test.
      dimensions (dict of str: str): Requested dimensions of the test.
      target_name: Ninja build target for the test. See
          //testing/buildbot/gn_isolate_map.pyl for more info.
      full_test_target: a fully qualified Ninja target, e.g.
        "//chrome/test:browser_tests".
      test_id_prefix: test_id_prefix: Test_id prefix used by ResultDB, e.g.
          "ninja://chrome/test:telemetry_gpu_integration_test/trace_test/".
      extra_suffix: Suffix applied to the test's step name in the build page.
      expiration: Expiration of the test in Swarming, in seconds.
      hard_timeout: Timeout of the test in Swarming, in seconds.
      io_timeout: Max amount of time in seconds Swarming will allow the task to
          be silent (no stdout or stderr).
      waterfall_mastername: Waterfall/console name for the test's builder.
      waterfall_buildername: Builder name for the test's builder.
      set_up: Optional set up scripts.
      tear_down: Optional tear_down scripts.
      optional_dimensions: (dict of expiration: [{dimension(str): val(str)]}:
          Optional dimensions that create additional fallback task slices.
      service_account: Service account to run the test as.
      isolate_coverage_data: Bool indicating wether to isolate coverage profile
          data during the task.
      isolate_profile_data: Bool indicating whether to isolate profile data
          during the task.
      merge: 'merge' dict as set in //testing/buildbot/ pyl files for the test.
      ignore_task_failure: If False, the test will be reported as StepFailure on
          failure.
      containment_type: Type of containment to use for the task. See
          `swarming.py trigger --help` for more info.
      idempotent: Wether to mark the task as idempotent. A value of None will
          cause chromium_swarming/api.py to apply its default_idempotent val.
      shards: Number of shards to trigger.
      cipd_packages: [(str, str, str)] list of 3-tuples containing cipd
          package root, package name, and package version.
      named_caches: {str: str} dict mapping named cache name to named cache
          path.
    """
    super(SwarmingTest, self).__init__(
        name,
        target_name=target_name,
        full_test_target=full_test_target,
        test_id_prefix=test_id_prefix,
        waterfall_mastername=waterfall_mastername,
        waterfall_buildername=waterfall_buildername,
        **kwargs)
    self._tasks = {}
    self._cipd_packages = cipd_packages or []
    self._containment_type = containment_type
    self._dimensions = dimensions
    self._optional_dimensions = optional_dimensions
    self._extra_suffix = extra_suffix
    self._expiration = expiration
    self._hard_timeout = hard_timeout
    self._io_timeout = io_timeout
    self._set_up = set_up
    self._merge = merge
    self._tear_down = tear_down
    self._isolate_coverage_data = isolate_coverage_data
    self._isolate_profile_data = isolate_profile_data
    self._ignore_task_failure = ignore_task_failure
    self._named_caches = named_caches or {}
    self._shards = shards
    self._service_account = service_account
    self._idempotent = idempotent
    if dimensions and not extra_suffix:
      if dimensions.get('gpu'):
        self._extra_suffix = self._get_gpu_suffix(dimensions)
      elif 'Android' == dimensions.get('os') and dimensions.get('device_type'):
        self._extra_suffix = self._get_android_suffix(dimensions)

  def _dispatches_to_windows(self):
    if self._dimensions:
      os = self._dimensions.get('os', '')
      return os.startswith('Windows')
    return False

  @staticmethod
  def _get_gpu_suffix(dimensions):
    gpu_vendor_id = dimensions.get('gpu', '').split(':')[0].lower()
    vendor_ids = {
      '8086': 'Intel',
      '10de': 'NVIDIA',
      '1002': 'ATI',
    }
    gpu_vendor = vendor_ids.get(gpu_vendor_id) or '(%s)' % gpu_vendor_id

    os = dimensions.get('os', '')
    if os.lower().startswith('mac'):
      if dimensions.get('hidpi', '') == '1':
        os_name = 'Mac Retina'
      else:
        os_name = 'Mac'
    elif os.lower().startswith('windows'):
      os_name = 'Windows'
    else:
      # TODO(crbug/1018836): Use distro specific name instead of Linux.
      os_name = 'Linux'

    return 'on %s GPU on %s' % (gpu_vendor, os_name)

  @staticmethod
  def _get_android_suffix(dimensions):
    device_codenames = {
      'angler': 'Nexus 6P',
      'athene': 'Moto G4',
      'bullhead': 'Nexus 5X',
      'dragon': 'Pixel C',
      'flo': 'Nexus 7 [2013]',
      'flounder': 'Nexus 9',
      'foster': 'NVIDIA Shield',
      'fugu': 'Nexus Player',
      'goyawifi': 'Galaxy Tab 3',
      'grouper': 'Nexus 7 [2012]',
      'hammerhead': 'Nexus 5',
      'herolte': 'Galaxy S7 [Global]',
      'heroqlteatt': 'Galaxy S7 [AT&T]',
      'j5xnlte': 'Galaxy J5',
      'm0': 'Galaxy S3',
      'mako': 'Nexus 4',
      'manta': 'Nexus 10',
      'marlin': 'Pixel 1 XL',
      'sailfish': 'Pixel 1',
      'shamu': 'Nexus 6',
      'sprout': 'Android One',
      'taimen': 'Pixel 2 XL',
      'walleye': 'Pixel 2',
      'zerofltetmo': 'Galaxy S6',
    }
    targetted_device = dimensions['device_type']
    product_name = device_codenames.get(targetted_device, targetted_device)
    return 'on Android device %s' % product_name

  @property
  def set_up(self):
    return self._set_up

  @property
  def tear_down(self):
    return self._tear_down

  @property
  def name(self):
    if self._extra_suffix:
      return '%s %s' % (self._name, self._extra_suffix)
    else:
      return self._name

  @property
  def canonical_name(self):
    """Canonical name of the test, no suffix attached."""
    return self._name

  @property
  def target_name(self):
    return self._target_name or self._name

  @property
  def runs_on_swarming(self):
    return True

  @property
  def isolate_coverage_data(self):
    return bool(self._isolate_coverage_data)

  @property
  def isolate_profile_data(self):
    # TODO(crbug.com/1075823) - delete isolate_coverage_data once deprecated.
    # Release branches will still be setting isolate_coverage_data under
    # src/testing. Deprecation expected after M83.
    return bool(self._isolate_profile_data) or self.isolate_coverage_data

  @property
  def shards(self):
    return self._shards

  def create_task(self, api, suffix, isolated):
    """Creates a swarming task. Must be overridden in subclasses.

    Args:
      api: Caller's API.
      suffix: Suffix added to the test name.
      isolated: Hash of the isolated test to be run.

    Returns:
      A SwarmingTask object.
    """
    raise NotImplementedError()  # pragma: no cover

  def _apply_swarming_task_config(
      self, task, api, suffix, isolated, filter_flag, filter_delimiter):
    """Applies shared configuration for swarming tasks.
    """
    tests_to_retry = self._tests_to_retry(suffix)
    test_options = _test_options_for_running(self.test_options, suffix,
                                             tests_to_retry)
    args = _merge_args_and_test_options(self, self._args, test_options)

    shards = self._shards

    if tests_to_retry:
      # The filter list is eventually passed to the binary over the command
      # line.  On Windows, the command line max char limit is 8191 characters.
      # On other OSes, the max char limit is over 100,000 characters. We avoid
      # sending the filter list if we're close to the limit -- this causes all
      # tests to be run.
      char_limit = 6000 if self._dispatches_to_windows() else 90000
      expected_filter_length = (sum(len(x) for x in tests_to_retry) +
          len(tests_to_retry) * len(filter_delimiter))

      if expected_filter_length < char_limit:
        test_list = filter_delimiter.join(tests_to_retry)
        args = _merge_arg(args, filter_flag, test_list)
        shards = self.shards_to_retry_with(shards, len(tests_to_retry))

    task.extra_args.extend(args)
    task.shards = shards

    task_request = task.request
    task_slice = task_request[0]

    using_pgo = api.chromium_tests.m.pgo.using_pgo
    if self.isolate_profile_data or using_pgo:
      # Targets built with 'use_clang_coverage' or 'use_clang_profiling' (also
      # set by chrome_pgo_phase=1) will look at this environment variable to
      # determine where to write the profile dumps. The %Nm syntax is understood
      # by this instrumentation, see:
      #   https://clang.llvm.org/docs/SourceBasedCodeCoverage.html#id4
      task_slice = task_slice.with_env_vars(**{
          'LLVM_PROFILE_FILE':
              '${ISOLATED_OUTDIR}/profraw/default-%2m.profraw',
      })

      sparse = True
      skip_validation = False

      # code coverage runs llvm-profdata merge with --sparse. PGO does not.
      if using_pgo:
        sparse = False
        skip_validation = True
      # TODO(crbug.com/1076055) - Refactor this to the profiles recipe_module
      # Wrap the merge script specific to the test type (i.e. gtest vs isolated
      # script tests) in a wrapper that knows how to merge coverage/pgo profile
      # data. If the test object does not specify a merge script, use the one
      # defined by the swarming task in the chromium_swarm module. (The default
      # behavior for non-coverage/non-profile tests).
      self._merge = api.chromium_tests.m.code_coverage.shard_merge(
          self.step_name(suffix),
          self.target_name,
          skip_validation=skip_validation,
          sparse=sparse,
          additional_merge=self._merge or task.merge)

    if suffix.startswith('retry shards'):
      task_slice = task_slice.with_idempotent(False)
    elif self._idempotent is not None:
      task_slice = task_slice.with_idempotent(self._idempotent)

    if suffix == 'retry shards with patch':
      task.task_to_retry = self._tasks['with patch']
      assert task.task_to_retry, (
          '\'retry_shards_with_patch\' expects that the \'with patch\' phase '
          'has already run, but it apparently hasn\'t.')
      task.shard_indices = task.task_to_retry.failed_shards
      # Test suite failure is determined by merging and examining the JSON
      # output from the shards. Failed shards are determined by looking at the
      # swarming output [retcode !=0 or state != 'SUCCESS']. It is possible that
      # these are not in sync. This will cause no tasks to be dispatched for
      # 'retry shards with patch'. This error has graceful recovery: 'retry
      # shards with patch' will simply reuse results from 'with patch'.
      # Regardless, we want to emit a failing step so that the error is not
      # overlooked.
      if len(task.shard_indices) == 0: # pragma: no cover
        api.python.failing_step(
          'missing failed shards',
          "Retry shards with patch is being run on {}, which has no failed "
          "shards. This usually happens because of a test runner bug. The test "
          "runner reports test failures, but had exit_code 0.".format(
              self.step_name(suffix='with patch')))
    else:
      task.shard_indices = range(task.shards)

    task.build_properties = api.chromium.build_properties
    task.containment_type = self._containment_type
    task.ignore_task_failure = self._ignore_task_failure
    if self._merge:
      task.merge = self._merge

    task.trigger_script = self._trigger_script

    ensure_file = task_slice.cipd_ensure_file
    if self._cipd_packages:
      for package in self._cipd_packages:
        ensure_file.add_package(package[1], package[2], package[0])

    task_slice = (task_slice.with_cipd_ensure_file(ensure_file).
                   with_isolated(isolated))

    if self._named_caches:
      task.named_caches.update(self._named_caches)

    if suffix in self.SUFFIXES_TO_INCREASE_PRIORITY:
      task_request = task_request.with_priority(task_request.priority - 1)

    if self._expiration:
      task_slice = task_slice.with_expiration_secs(self._expiration)

    if self._hard_timeout:
      task_slice = task_slice.with_execution_timeout_secs(self._hard_timeout)

    if self._io_timeout:
      task_slice = task_slice.with_io_timeout_secs(self._io_timeout)

    task_dimensions = task_slice.dimensions
    # Add custom dimensions.
    if self._dimensions:  # pragma: no cover
      #TODO(stip): concoct a test case that will trigger this codepath
      for k, v in self._dimensions.iteritems():
        task_dimensions[k] = v
    # Set default value.
    if 'os' not in task_dimensions:
      task_dimensions['os'] = api.chromium_swarming.prefered_os_dimension(
          api.platform.name)
    task_slice = task_slice.with_dimensions(**task_dimensions)

    # Add optional dimensions.
    task.optional_dimensions = self._optional_dimensions or None

    # Add tags.
    tags = {
        'ninja_target': [self.full_test_target or ''],
        'test_id_prefix': [self.test_id_prefix or ''],
        'test_suite': [self.canonical_name],
    }

    task.request = (task_request.with_slice(0, task_slice).
                      with_name(self.step_name(suffix)).
                      with_service_account(self._service_account or '').
                      with_tags(tags))
    return task

  def get_task(self, suffix):
    return self._tasks.get(suffix)

  def pre_run(self, api, suffix):
    """Launches the test on Swarming."""
    assert suffix not in self._tasks, (
        'Test %s was already triggered' % self.step_name(suffix))

    # *.isolated may be missing if *_run target is misconfigured. It's a error
    # in gyp, not a recipe failure. So carry on with recipe execution.
    isolated = api.isolate.isolated_tests.get(self.isolate_target)
    if not isolated:
      return api.python.failing_step(
          '[error] %s' % self.step_name(suffix),
          '*.isolated file for target %s is missing' % self.isolate_target)

    # Create task.
    self._tasks[suffix] = self.create_task(api, suffix, isolated)

    return api.chromium_swarming.trigger_task(self._tasks[suffix])

  def validate_task_results(self, api, step_result):
    """Interprets output of a task (provided as StepResult object).

    Called for successful and failed tasks.

    Args:
      api: Caller's API.
      step_result: StepResult object to examine.

    Returns:
      A dictionary with the keys: (valid, failures, total_tests_ran,
      pass_fail_counts), where:
        * valid is True if valid results are available
        * failures is a list of names of failed tests (ignored if valid is
            False).
        * total_tests_ran counts the number of tests executed.
        * pass_fail_counts is a dictionary that includes the number of passes
            and fails for each test.
        * findit_notrun is a set of tests for which every test result was NOTRUN
          or UNKNOWN. This is a temporary placeholder to simplify FindIt logic.
    """
    raise NotImplementedError()  # pragma: no cover

  @recipe_api.composite_step
  def run(self, api, suffix):
    """Waits for launched test to finish and collects the results."""
    assert suffix not in self._test_runs, (
        'Results of %s were already collected' % self.step_name(suffix))

    # Emit error if test wasn't triggered. This happens if *.isolated is not
    # found. (The build is already red by this moment anyway).
    if suffix not in self._tasks:
      return api.python.failing_step(
          '[collect error] %s' % self.step_name(suffix),
          '%s wasn\'t triggered' % self.target_name)

    step_result, has_valid_results = api.chromium_swarming.collect_task(
      self._tasks[suffix])
    self._suffix_step_name_map[suffix] = '.'.join(step_result.name_tokens)

    metadata = self.step_metadata(suffix)
    step_result.presentation.logs['step_metadata'] = (json.dumps(
        metadata, sort_keys=True, indent=2)).splitlines()

    # TODO(martiniss): Consider moving this into some sort of base
    # validate_task_results implementation.
    results = self.validate_task_results(api, step_result)
    if not has_valid_results:
      results['valid'] = False

    self.update_test_run(api, suffix, results)
    return step_result

  @property
  def uses_isolate(self):
    return True

  def step_metadata(self, suffix=None):
    data = super(SwarmingTest, self).step_metadata(suffix)
    if suffix is not None:
      data['full_step_name'] = self._suffix_step_name_map[suffix]
      data['patched'] = suffix in (
          'with patch', 'retry shards with patch')
      data['dimensions'] = self._tasks[suffix].request[0].dimensions
      data['swarm_task_ids'] = self._tasks[suffix].get_task_ids()
    return data


class SwarmingGTestTest(SwarmingTest):

  def __init__(self,
               name,
               args=None,
               target_name=None,
               full_test_target=None,
               test_id_prefix=None,
               shards=1,
               dimensions=None,
               extra_suffix=None,
               expiration=None,
               hard_timeout=None,
               io_timeout=None,
               override_compile_targets=None,
               waterfall_mastername=None,
               waterfall_buildername=None,
               merge=None,
               trigger_script=None,
               set_up=None,
               tear_down=None,
               isolate_coverage_data=False,
               isolate_profile_data=False,
               optional_dimensions=None,
               service_account=None,
               containment_type=None,
               ignore_task_failure=False,
               **kw):
    super(SwarmingGTestTest, self).__init__(
        name,
        dimensions,
        target_name,
        full_test_target,
        test_id_prefix,
        extra_suffix,
        expiration,
        hard_timeout,
        io_timeout,
        waterfall_mastername=waterfall_mastername,
        waterfall_buildername=waterfall_buildername,
        set_up=set_up,
        tear_down=tear_down,
        isolate_coverage_data=isolate_coverage_data,
        isolate_profile_data=isolate_profile_data,
        merge=merge,
        shards=shards,
        ignore_task_failure=ignore_task_failure,
        optional_dimensions=optional_dimensions,
        service_account=service_account,
        containment_type=containment_type,
        **kw)
    self._args = args or []
    self._override_compile_targets = override_compile_targets
    self._gtest_results = {}
    self._trigger_script = trigger_script

  @Test.test_options.setter
  def test_options(self, value):
    self._test_options = value

  @property
  def is_gtest(self):
    return True

  def compile_targets(self):
    if self._override_compile_targets:
      return self._override_compile_targets
    return [self.target_name]

  def create_task(self, api, suffix, isolated):
    task = api.chromium_swarming.gtest_task()
    self._apply_swarming_task_config(
        task, api, suffix, isolated, '--gtest_filter', ':')
    return task

  def validate_task_results(self, api, step_result):
    return step_result.test_utils.gtest_results.canonical_result_format()

  def pass_fail_counts(self, suffix):
    return self._gtest_results[suffix].pass_fail_counts

  @recipe_api.composite_step
  def run(self, api, suffix):
    """Waits for launched test to finish and collects the results."""
    step_result = super(SwarmingGTestTest, self).run(api, suffix)
    step_name = '.'.join(step_result.name_tokens)
    self._suffix_step_name_map[suffix] = step_name
    gtest_results = step_result.test_utils.gtest_results
    self._gtest_results[suffix] = gtest_results
    # Only upload test results if we have gtest results.
    if gtest_results and gtest_results.raw:
      parsed_gtest_data = gtest_results.raw
      chrome_revision_cp = api.bot_update.last_returned_properties.get(
          'got_revision_cp', 'refs/x@{#0}')
      _, chrome_revision = api.commit_position.parse(chrome_revision_cp)
      chrome_revision = str(chrome_revision)
      api.test_results.upload(
          api.json.input(parsed_gtest_data),
          chrome_revision=chrome_revision,
          test_type=step_name)
    return step_result


class LocalIsolatedScriptTest(Test):

  def __init__(self,
               name,
               args=None,
               target_name=None,
               override_compile_targets=None,
               results_handler=None,
               set_up=None,
               tear_down=None,
               isolate_coverage_data=None,
               isolate_profile_data=None,
               **runtest_kwargs):
    """Constructs an instance of LocalIsolatedScriptTest.

    An LocalIsolatedScriptTest knows how to invoke an isolate which obeys a
    certain contract. The isolate's main target must be a wrapper script which
    must interpret certain command line arguments as follows:

      --isolated-script-test-output [FILENAME]

    The wrapper script must write the simplified json output that the recipes
    consume (similar to GTestTest and ScriptTest) into |FILENAME|.

    The contract may be expanded later to support functionality like sharding
    and retries of specific failed tests. Currently the examples of such wrapper
    scripts live in src/testing/scripts/ in the Chromium workspace.

    Args:
      name: Displayed name of the test. May be modified by suffixes.
      args: Arguments to be passed to the test.
      target_name: Actual name of the test. Defaults to name.
      runtest_kwargs: Additional keyword args forwarded to the runtest.
      override_compile_targets: The list of compile targets to use. If not
        specified this is the same as target_name.
      set_up: Optional set up scripts.
      tear_down: Optional tear_down scripts.
    """
    super(LocalIsolatedScriptTest, self).__init__(name, target_name=target_name)
    self._args = args or []
    # FIXME: This should be a named argument, rather than catching all keyword
    # arguments to this constructor.
    self._runtest_kwargs = runtest_kwargs
    self._override_compile_targets = override_compile_targets
    self._set_up = set_up
    self._tear_down = tear_down
    self.results_handler = results_handler or JSONResultsHandler()
    self._isolate_coverage_data = isolate_coverage_data
    self._isolate_profile_data = isolate_profile_data

  @property
  def set_up(self):
    return self._set_up

  @property
  def tear_down(self):
    return self._tear_down

  @property
  def name(self):
    return self._name

  @property
  def target_name(self):
    return self._target_name or self._name

  @property
  def uses_isolate(self):
    return True

  @property
  def isolate_profile_data(self):
    # TODO(crbug.com/1075823) - delete isolate_coverage_data once deprecated
    # Release branches will still be setting isolate_coverage_data under
    # src/testing. Deprecation expected after M83.
    return self._isolate_profile_data or self._isolate_coverage_data

  def compile_targets(self):
    if self._override_compile_targets:
      return self._override_compile_targets
    return [self.target_name]

  @Test.test_options.setter
  def test_options(self, value):
    self._test_options = value

  # TODO(nednguyen, kbr): figure out what to do with Android.
  # (crbug.com/533480)
  @recipe_api.composite_step
  def run(self, api, suffix):
    tests_to_retry = self._tests_to_retry(suffix)
    test_options = _test_options_for_running(self.test_options, suffix,
                                             tests_to_retry)
    args = _merge_args_and_test_options(self, self._args, test_options)

    # TODO(nednguyen, kbr): define contract with the wrapper script to rerun
    # a subset of the tests. (crbug.com/533481)

    json_results_file = api.json.output()
    args.extend(
        ['--isolated-script-test-output', json_results_file])

    step_test_data = lambda: api.json.test_api.output(
        {'valid': True, 'failures': []})

    kwargs = {}
    if self.isolate_profile_data:
      kwargs.update({
          # Targets built with 'use_clang_coverage' will look at this
          # environment variable to determine where to write the profile dumps.
          # The %Nm syntax # is understood by this instrumentation, see:
          #   https://clang.llvm.org/docs/SourceBasedCodeCoverage.html#id4
          # We use one profile only as this is meant for short, single-process
          # tests. Anything longer or more complex should be running on swarming
          # instead of locally.
          'env': {
              'LLVM_PROFILE_FILE':
                  '${ISOLATED_OUTDIR}/profraw/default-%1m.profraw', },
          # The results of the script will be isolated, and the .isolate will be
          # dumped to stdout.
          'stdout': api.raw_io.output(),
      })

    try:
      api.isolate.run_isolated(
          self.name,
          api.isolate.isolated_tests[self.target_name],
          args,
          step_test_data=step_test_data, **kwargs)
    finally:
      # TODO(kbr, nedn): the logic of processing the output here is very similar
      # to that of SwarmingIsolatedScriptTest. They probably should be shared
      # between the two.
      step_result = api.step.active_result
      self._suffix_step_name_map[suffix] = '.'.join(step_result.name_tokens)
      results = step_result.json.output
      presentation = step_result.presentation

      test_results = api.test_utils.create_results_from_json(results)
      self.results_handler.render_results(api, test_results, presentation)

      self.update_test_run(
          api, suffix, self.results_handler.validate_results(api, results))

      if (api.step.active_result.retcode == 0 and
          not self._test_runs[suffix]['valid']):
        # This failure won't be caught automatically. Need to manually
        # raise it as a step failure.
        raise api.step.StepFailure(api.test_utils.INVALID_RESULTS_MAGIC)

    return self._test_runs[suffix]


class SwarmingIsolatedScriptTest(SwarmingTest):

  def __init__(self,
               name,
               args=None,
               target_name=None,
               full_test_target=None,
               test_id_prefix=None,
               shards=1,
               dimensions=None,
               extra_suffix=None,
               ignore_task_failure=False,
               expiration=None,
               hard_timeout=None,
               override_compile_targets=None,
               perf_id=None,
               results_url=None,
               perf_dashboard_id=None,
               io_timeout=None,
               waterfall_mastername=None,
               waterfall_buildername=None,
               merge=None,
               trigger_script=None,
               results_handler=None,
               set_up=None,
               tear_down=None,
               isolate_coverage_data=False,
               isolate_profile_data=False,
               optional_dimensions=None,
               service_account=None,
               **kw):
    super(SwarmingIsolatedScriptTest, self).__init__(
        name,
        dimensions,
        target_name,
        full_test_target,
        test_id_prefix,
        extra_suffix,
        expiration,
        hard_timeout,
        io_timeout,
        waterfall_mastername=waterfall_mastername,
        waterfall_buildername=waterfall_buildername,
        set_up=set_up,
        tear_down=tear_down,
        isolate_coverage_data=isolate_coverage_data,
        isolate_profile_data=isolate_profile_data,
        merge=merge,
        shards=shards,
        ignore_task_failure=ignore_task_failure,
        optional_dimensions=optional_dimensions,
        service_account=service_account,
        **kw)
    self._args = args or []
    self._override_compile_targets = override_compile_targets
    self._perf_id=perf_id
    self._results_url = results_url
    self._perf_dashboard_id = perf_dashboard_id
    self._isolated_script_results = {}
    self._trigger_script = trigger_script
    self.results_handler = results_handler or JSONResultsHandler(
        ignore_task_failure=ignore_task_failure)

  @property
  def target_name(self):
    return self._target_name or self._name

  def compile_targets(self):
    if self._override_compile_targets:
      return self._override_compile_targets
    return [self.target_name]

  @property
  def uses_isolate(self):
    return True

  @Test.test_options.setter
  def test_options(self, value):
    self._test_options = value

  def create_task(self, api, suffix, isolated):
    task = api.chromium_swarming.isolated_script_task()

    task_slice = task.request[0]
    task.request = task.request.with_slice(0, task_slice)

    self._apply_swarming_task_config(
        task, api, suffix, isolated, '--isolated-script-test-filter', '::')
    return task

  def validate_task_results(self, api, step_result):
    if getattr(step_result, 'json') and getattr(step_result.json, 'output'):
      results_json = step_result.json.output
    else:
      results_json = {}

    test_run_dictionary = (
        self.results_handler.validate_results(api, results_json))
    presentation = step_result.presentation

    test_results = api.test_utils.create_results_from_json(results_json)
    self.results_handler.render_results(api, test_results, presentation)

    self._isolated_script_results = results_json

    # Even if the output is valid, if the return code is greater than
    # MAX_FAILURES_EXIT_STATUS then the test did not complete correctly and the
    # results can't be trusted. It probably exited early due to a large number
    # of failures or an environment setup issue.
    if step_result.retcode > api.test_utils.MAX_FAILURES_EXIT_STATUS:
      test_run_dictionary['valid'] = False

    return test_run_dictionary

  @recipe_api.composite_step
  def run(self, api, suffix):
    step_result = super(SwarmingIsolatedScriptTest, self).run(api, suffix)
    results = self._isolated_script_results

    if results:
      # Noted when uploading to test-results, the step_name is expected to be an
      # exact match to the step name on the build.
      self.results_handler.upload_results(
          api, results, '.'.join(step_result.name_tokens),
          not bool(self.deterministic_failures(suffix)), suffix)
    return step_result


class PythonBasedTest(Test):
  def __init__(self, name, **kwargs):
    super(PythonBasedTest, self).__init__(name, **kwargs)

  def compile_targets(self):
    return []  # pragma: no cover

  def run_step(self, api, suffix, cmd_args, **kwargs):
    raise NotImplementedError()  # pragma: no cover

  @recipe_api.composite_step
  def run(self, api, suffix):
    # These arguments must be passed to an invocation of the recipe engine. The
    # recipe engine will recognize that the second argument is a subclass of
    # OutputPlaceholder and use that to populate
    # step_result.test_utils.test_results.
    cmd_args = ['--write-full-results-to',
                api.test_utils.test_results(add_json_log=False)]
    tests_to_retry = self._tests_to_retry(suffix)
    if tests_to_retry:
      cmd_args.extend(tests_to_retry)  # pragma: no cover

    default_factory_for_tests = (lambda:
        api.test_utils.test_api.canned_test_output(passing=True))
    step_result = self.run_step(
        api,
        suffix,
        cmd_args,
        step_test_data=default_factory_for_tests,
        ok_ret='any')
    self._suffix_step_name_map[suffix] = '.'.join(step_result.name_tokens)
    test_results = step_result.test_utils.test_results
    presentation = step_result.presentation
    if (test_results.valid and
        step_result.retcode <= api.test_utils.MAX_FAILURES_EXIT_STATUS):
      self.update_test_run(
          api, suffix, test_results.canonical_result_format())
      _, failures = api.test_utils.limit_failures(
          test_results.unexpected_failures.keys())
      presentation.step_text += api.test_utils.format_step_text([
          ['unexpected_failures:', failures],
      ])
      if failures:
        presentation.status = api.step.FAILURE
    else:
      self.update_test_run(
          api, suffix, api.test_utils.canonical.result_format())
      presentation.status = api.step.EXCEPTION
      presentation.step_text = api.test_utils.INVALID_RESULTS_MAGIC

    return step_result


class AndroidTest(Test):
  def __init__(self, name, compile_targets, waterfall_mastername=None,
               waterfall_buildername=None):
    super(AndroidTest, self).__init__(
        name, waterfall_mastername=waterfall_mastername,
        waterfall_buildername=waterfall_buildername)
    self._compile_targets = compile_targets

  def run_tests(self, api, suffix, json_results_file):
    """Runs the Android test suite and outputs the json results to a file.

    Args:
      api: Caller's API.
      suffix: Suffix added to the test name.
      json_results_file: File to output the test results.
    """
    raise NotImplementedError()  # pragma: no cover

  @recipe_api.composite_step
  def run(self, api, suffix):
    assert api.chromium.c.TARGET_PLATFORM == 'android'

    json_results_file = api.test_utils.gtest_results(add_json_log=False)
    try:
      step_result = self.run_tests(api, suffix, json_results_file)
    except api.step.StepFailure as f:
      step_result = f.result
      raise
    finally:
      self._suffix_step_name_map[suffix] = '.'.join(step_result.name_tokens)
      self.update_test_run(
          api, suffix, api.test_utils.canonical.result_format())
      presentation_step = api.python.succeeding_step(
          'Report %s results' % self.name, '')
      gtest_results = api.test_utils.present_gtest_failures(
          step_result, presentation=presentation_step.presentation)
      if gtest_results:
        self.update_test_run(
            api, suffix, gtest_results.canonical_result_format())

        api.test_results.upload(
            api.json.input(gtest_results.raw),
            test_type='.'.join(step_result.name_tokens),
            chrome_revision=api.bot_update.last_returned_properties.get(
                'got_revision_cp', 'refs/x@{#0}'))

    return step_result

  def compile_targets(self):
    return self._compile_targets


class AndroidJunitTest(AndroidTest):

  def __init__(self,
               name,
               target_name=None,
               additional_args=None,
               waterfall_mastername=None,
               waterfall_buildername=None):
    target_name = target_name or name
    super(AndroidJunitTest, self).__init__(
        name,
        compile_targets=[target_name],
        waterfall_mastername=None,
        waterfall_buildername=None)
    self._additional_args = additional_args
    self._target_name = target_name

  @property
  def uses_local_devices(self):
    return False

  #override
  def run_tests(self, api, suffix, json_results_file):
    return api.chromium_android.run_java_unit_test_suite(
        self.name,
        target_name=self._target_name,
        verbose=True,
        suffix=suffix,
        additional_args=self._additional_args,
        json_results_file=json_results_file,
        step_test_data=(
            lambda: api.test_utils.test_api.canned_gtest_output(False)))


class BlinkTest(Test):
  # TODO(dpranke): This should be converted to a PythonBasedTest, although it
  # will need custom behavior because we archive the results as well.
  def __init__(self, extra_args=None):
    super(BlinkTest, self).__init__('blink_web_tests')
    self._extra_args = extra_args
    self.results_handler = LayoutTestResultsHandler()

  def compile_targets(self):
    return ['blink_tests']

  @property
  def uses_local_devices(self):
    return True

  @recipe_api.composite_step
  def run(self, api, suffix):
    results_dir = api.path['start_dir'].join('layout-test-results')

    step_name = self.step_name(suffix)
    args = [
        '--target', api.chromium.c.BUILD_CONFIG,
        '--results-directory', results_dir,
        '--build-dir', api.chromium.c.build_dir,
        '--json-test-results', api.test_utils.test_results(add_json_log=False),
        '--master-name', api.properties['mastername'],
        '--build-number', str(api.buildbucket.build.number),
        '--builder-name', api.buildbucket.builder_name,
        '--step-name', step_name,
        '--no-show-results',
        '--clobber-old-results',  # Clobber test results before each run.
        '--exit-after-n-failures', '5000',
        '--exit-after-n-crashes-or-timeouts', '100',
        '--debug-rwt-logging',

        # layout test failures are retried 3 times when '--test-list' is not
        # passed, but only once when '--test-list' is passed. We want to always
        # retry 3 times, so we explicitly specify it.
        '--num-retries', '3',
    ]

    if api.chromium.c.TARGET_PLATFORM == 'android':
      args.extend(['--platform', 'android'])

    if self._extra_args:
      args.extend(self._extra_args)

    tests_to_retry = self._tests_to_retry(suffix)
    if tests_to_retry:
      test_list = "\n".join(tests_to_retry)
      args.extend(['--test-list', api.raw_io.input_text(test_list),
                   '--skipped', 'always'])

    try:
      default_factory_for_tests = (lambda:
          api.test_utils.test_api.canned_test_output(passing=True,
                                                     minimal=True))
      step_result = api.python(
        step_name,
        api.path['checkout'].join('third_party', 'blink', 'tools',
                                  'run_web_tests.py'),
        args,
        step_test_data=default_factory_for_tests)

      # Mark steps with unexpected flakes as warnings. Do this here instead of
      # "finally" blocks because we only want to do this if step was successful.
      # We don't want to possibly change failing steps to warnings.
      if step_result and step_result.test_utils.test_results.unexpected_flakes:
        step_result.presentation.status = api.step.WARNING
    finally:
      step_result = api.step.active_result
      self._suffix_step_name_map[suffix] = '.'.join(step_result.name_tokens)

      # TODO(dpranke): crbug.com/357866 - note that all comparing against
      # MAX_FAILURES_EXIT_STATUS tells us is that we did not exit early
      # or abnormally; it does not tell us how many failures there actually
      # were, which might be much higher (up to 5000 diffs, where we
      # would bail out early with --exit-after-n-failures) or lower
      # if we bailed out after 100 crashes w/ -exit-after-n-crashes, in
      # which case the retcode is actually 130
      if step_result.retcode > api.test_utils.MAX_FAILURES_EXIT_STATUS:
        self.update_test_run(
            api, suffix, api.test_utils.canonical.result_format())
      else:
        self.update_test_run(
            api, suffix, step_result.test_utils.test_results.
            canonical_result_format())

      if step_result:
        results = step_result.test_utils.test_results

        self.results_handler.render_results(
            api, results, step_result.presentation)

        self.results_handler.upload_results(
            api, results, '.'.join(step_result.name_tokens),
            not bool(self.deterministic_failures(suffix)), suffix)

    return step_result


class MiniInstallerTest(PythonBasedTest):  # pylint: disable=W0232
  def __init__(self, **kwargs):
    super(MiniInstallerTest, self).__init__('test_installer', **kwargs)

  def compile_targets(self):
    return ['mini_installer_tests']

  def run_step(self, api, suffix, cmd_args, **kwargs):
    test_path = api.path['checkout'].join('chrome', 'test', 'mini_installer')
    args = [
      '--build-dir', api.chromium.c.build_dir,
      '--target', api.chromium.c.build_config_fs,
      '--force-clean',
      '--config', test_path.join('config', 'config.config'),
    ]
    args.extend(cmd_args)
    return api.python(
      self.step_name(suffix),
      test_path.join('test_installer.py'),
      args,
      **kwargs)


class IncrementalCoverageTest(Test):
  def __init__(self, **kwargs):
    super(IncrementalCoverageTest, self).__init__(
        'incremental coverage', **kwargs)

  @property
  def uses_local_devices(self):
    return True

  def has_valid_results(self, suffix):
    return True

  def failures(self, suffix):
    return []

  def pass_fail_counts(self, suffix): # pragma: no cover
    return {}

  def compile_targets(self):
    """List of compile targets needed by this test."""
    return []

  @recipe_api.composite_step
  def run(self, api, suffix):
    step_result = api.chromium_android.coverage_report(upload=False)
    self._suffix_step_name_map[suffix] = '.'.join(step_result.name_tokens)
    api.chromium_android.get_changed_lines_for_revision()
    api.chromium_android.incremental_coverage_report()
    return step_result

class FindAnnotatedTest(Test):
  _TEST_APKS = {
      'chrome_public_test_apk': 'ChromePublicTest',
      'content_shell_test_apk': 'ContentShellTest',
      'system_webview_shell_layout_test_apk': 'SystemWebViewShellLayoutTest',
      'webview_instrumentation_test_apk': 'WebViewInstrumentationTest',
  }

  def __init__(self, **kwargs):
    super(FindAnnotatedTest, self).__init__('Find annotated test', **kwargs)

  def compile_targets(self):
    return FindAnnotatedTest._TEST_APKS.keys()

  @recipe_api.composite_step
  def run(self, api, suffix):
    temp_output_dir = api.path.mkdtemp('annotated_tests_json')
    timestamp_string = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%S')
    if api.buildbucket.builder_name:
      timestamp_string = api.properties.get('current_time', timestamp_string)

    args = [
        '--apk-output-dir', api.chromium.output_dir,
        '--json-output-dir', temp_output_dir,
        '--timestamp-string', timestamp_string,
        '-v']
    args.extend(
        ['--test-apks'] + [i for i in FindAnnotatedTest._TEST_APKS.values()])
    with api.context(cwd=api.path['checkout']):
      step_result = api.python(
          'run find_annotated_tests.py',
          api.path['checkout'].join(
              'tools', 'android', 'find_annotated_tests.py'),
          args=args)
      self._suffix_step_name_map[suffix] = '.'.join(step_result.name_tokens)
    api.gsutil.upload(
        temp_output_dir.join(
            '%s-android-chrome.json' % timestamp_string),
        'chromium-annotated-tests', 'android')

    return step_result


class WebRTCPerfTest(LocalGTestTest):
  """A LocalGTestTest reporting perf metrics.

  WebRTC is the only project that runs correctness tests with perf reporting
  enabled at the same time, which differs from the chromium.perf bots.
  """

  def __init__(self, name, args, perf_id, commit_position_property,
               **runtest_kwargs):
    """Construct a WebRTC Perf test.

    Args:
      name: Name of the test.
      args: Command line argument list.
      perf_id: String identifier (preferably unique per machine).
      commit_position_property: Commit position property for the Chromium
        checkout. It's needed because for chromium.webrtc.fyi 'got_revision_cp'
        refers to WebRTC's commit position instead of Chromium's, so we have to
        use 'got_cr_revision_cp' instead.
    """
    assert perf_id
    # TODO(kjellander): See if it's possible to rely on the build spec
    # properties 'perf-id' and 'results-url' as set in the
    # chromium_tests/chromium_perf.py. For now, set these to get an exact
    # match of our current expectations.
    runtest_kwargs['perf_id'] = perf_id
    runtest_kwargs['results_url'] = RESULTS_URL

    # TODO(kjellander): See if perf_dashboard_id is still needed.
    runtest_kwargs['perf_dashboard_id'] = name
    runtest_kwargs['annotate'] = 'graphing'
    super(WebRTCPerfTest, self).__init__(
        name, args, commit_position_property=commit_position_property,
        **runtest_kwargs)

  @recipe_api.composite_step
  def run(self, api, suffix):
    self._wire_up_perf_config(api)
    result = super(WebRTCPerfTest, self).run(api, suffix)

    # These runs do not return json data about which tests were executed
    # as they report to ChromePerf dashboard.
    # Here we just need to be sure that all tests have passed.
    if result.retcode == 0:
      self.update_test_run(api, suffix,
                           api.test_utils.canonical.result_format(valid=True))
    return result


  def _wire_up_perf_config(self, api):
    props = api.bot_update.last_returned_properties
    perf_config = { 'a_default_rev': 'r_webrtc_git' }

    # 'got_webrtc_revision' property is present for bots in both chromium.webrtc
    # and chromium.webrtc.fyi in reality, but due to crbug.com/713356, the
    # latter don't get properly simulated. Fallback to got_revision then.
    webrtc_rev = props.get('got_webrtc_revision', props['got_revision'])

    perf_config['r_webrtc_git'] = webrtc_rev

    self._runtest_kwargs['perf_config'] = perf_config


class MockTest(Test):
  """A Test solely intended to be used in recipe tests."""

  class ExitCodes(object):
    FAILURE = 1
    INFRA_FAILURE = 2

  def __init__(self,
               name='MockTest',
               target_name=None,
               full_test_target=None,
               test_id_prefix=None,
               waterfall_mastername=None,
               waterfall_buildername=None,
               abort_on_failure=False,
               has_valid_results=True,
               failures=None,
               runs_on_swarming=False,
               per_suffix_failures=None,
               per_suffix_valid=None,
               api=None):
    super(MockTest, self).__init__(waterfall_mastername, waterfall_buildername)
    self._target_name = target_name
    self._full_test_target = full_test_target
    self._test_id_prefix = test_id_prefix
    self._abort_on_failure = abort_on_failure
    self._failures = failures or []
    self._has_valid_results = has_valid_results
    self._per_suffix_failures = per_suffix_failures or {}
    self._per_suffix_valid = per_suffix_valid or {}
    self._name = name
    self._runs_on_swarming = runs_on_swarming
    self._api = api

  @property
  def name(self):
    return self._name

  @property
  def runs_on_swarming(self): # pragma: no cover
    return self._runs_on_swarming

  @contextlib.contextmanager
  def _mock_exit_codes(self, api):
    try:
      yield
    except api.step.StepFailure as f:
      if f.result.retcode == self.ExitCodes.INFRA_FAILURE:
        i = api.step.InfraFailure(f.name, result=f.result)
        i.result.presentation.status = api.step.EXCEPTION
        raise i
      self._failures.append('test_failure')
      raise

  def _mock_suffix(self, suffix):
    return ' (%s)' % suffix if suffix else ''

  def pre_run(self, api, suffix):
    with self._mock_exit_codes(api):
      api.step('pre_run %s%s' % (self.name, self._mock_suffix(suffix)), None)

  @recipe_api.composite_step
  def run(self, api, suffix):
    with self._mock_exit_codes(api):
      step_result = api.step(
          '%s%s' % (self.name, self._mock_suffix(suffix)), None)
      self._suffix_step_name_map[suffix] = '.'.join(step_result.name_tokens)

    return step_result

  def has_valid_results(self, suffix):
    self._api.step(
        'has_valid_results %s%s' % (self.name, self._mock_suffix(suffix)), None)
    if suffix in self._per_suffix_valid: # pragma: no cover
      return self._per_suffix_valid[suffix]
    return self._has_valid_results

  def failures(self, suffix):
    self._api.step(
        'failures %s%s' % (self.name, self._mock_suffix(suffix)), None)
    if suffix in self._per_suffix_failures: # pragma: no cover
      return self._per_suffix_failures[suffix]
    return self._failures

  def deterministic_failures(self, suffix):
    """Use same logic as failures for the Mock test."""
    return self.failures(suffix)

  def pass_fail_counts(self, suffix):
    return {}

  def compile_targets(self): # pragma: no cover
    return []

  @property
  def abort_on_failure(self):
    return self._abort_on_failure

class SwarmingIosTest(SwarmingTest):
  def __init__(self, swarming_service_account, platform, config, task,
               upload_test_results, result_callback, use_test_data):
    """
    Args:
      swarming_service_account: A string representing the service account
                                that will trigger the task.
      platform: A string, either 'device' or 'simulator'
      config: A dictionary detailing the build config. This is an iOS-specific
              config that has no documentation.
      task: A dictionary detailing the task config. This is an iOS-specific
            config that has no documentation.
      upload_test_results: Upload test results JSON to the flakiness dashboard.
      result_callback: A function to call whenever a task finishes.
        It is called with these named args:
        * name: Name of the test ('test'->'app' attribute).
        * step_result: Step result object from the collect step.
        If the function is not provided, the default is to upload performance
        results from perf_result.json.
    """
    super(SwarmingIosTest, self).__init__(
        name=task['step name'],
        cipd_packages=[(
            MAC_TOOLCHAIN_ROOT,
            MAC_TOOLCHAIN_PACKAGE,
            MAC_TOOLCHAIN_VERSION,
        )])
    self._service_account = swarming_service_account
    self._platform = platform
    self._config = copy.deepcopy(config)
    self._task = copy.deepcopy(task)
    self._upload_test_results = upload_test_results
    self._result_callback = result_callback
    self._use_test_data = use_test_data
    self._args = []
    self._trigger_script = None

    replay_package_name = task['test'].get('replay package name')
    replay_package_version = task['test'].get('replay package version')
    use_trusted_cert = task['test'].get('use trusted cert')
    if use_trusted_cert or (replay_package_name and replay_package_version):
      self._cipd_packages.append((
          WPR_TOOLS_ROOT,
          WPR_TOOLS_PACKAGE,
          WPR_TOOLS_VERSION,
      ))
    if replay_package_name and replay_package_version:
      self._cipd_packages.append((
          WPR_REPLAY_DATA_ROOT,
          replay_package_name,
          replay_package_version,
      ))
    self._expiration = (self._task['test'].get('expiration_time') or
                        self._config.get( 'expiration_time'))

    self._hard_timeout = self._task['test'].get(
        'max runtime seconds') or self._config.get('max runtime seconds')

    self._optional_dimensions = task['test'].get(
        'optional_dimensions')
    if self._optional_dimensions:
      for dimension_list in self._optional_dimensions.values():
        for dimension_set in dimension_list:
          if self._platform == 'simulator' and 'host os' in dimension_set:
            # We don't want both values to be set, as the syntax for
            # this won't work quite right in the swarming task api, we have
            # no good way to specify the value twice. And, there should
            # be no need for this.
            # TODO(crbug.com/955856): we should just move away from 'host os'.
            assert 'os' not in dimension_set
            dimension_set['os'] = dimension_set['host os']
            dimension_set.pop('host os')

    self._dimensions = {
        'pool': 'chromium.tests',
    }

    # TODO(crbug.com/835036): remove this when all configs are migrated to
    # "xcode build version". Otherwise keep it for backwards compatibility;
    # otherwise we may receive an older Mac OS which does not support the
    # requested Xcode version.
    if task.get('xcode version'):
      self._dimensions['xcode_version'] = task['xcode version']

    if self._platform == 'simulator':
      # TODO(crbug.com/955856): We should move away from 'host os'.
      self._dimensions['os'] = task['test'].get('host os') or 'Mac'
    elif self._platform == 'device':
      self._dimensions['os'] = 'iOS-%s' % str(task['test']['os'])
      if self._config.get('device check'):
        self._dimensions['device_status'] = 'available'
      self._dimensions['device'] = IOS_PRODUCT_TYPES.get(
        task['test']['device type'])
    if task['bot id']:
      self._dimensions['id'] = task['bot id']
    if task['pool']:
      self._dimensions['pool'] = task['pool']


  def pre_run(self, api, suffix):
    task = self._task

    task['tmp_dir'] = api.path.mkdtemp(task['task_id'])

    swarming_task = api.chromium_swarming.task(
      name=task['step name'],
      task_output_dir=task['tmp_dir'],
      failure_as_exception=False,
    )
    self._apply_swarming_task_config(
        swarming_task, api, suffix, task['isolated hash'], filter_flag=None,
        filter_delimiter=None)

    task_slice = swarming_task.request[0]

    # The implementation of _apply_swarming_task_config picks up default
    # dimensions which don't work for iOS because the swarming bots do not
    # specify typical dimensions [GPU, cpu type]. We explicitly override
    # dimensions here to get the desired results.
    task_slice = task_slice.with_dimensions(**self._dimensions)
    swarming_task.request = (swarming_task.request.
                              with_slice(0, task_slice).
                              with_priority(task['test'].get('priority', 200)))

    if self._platform == 'device' and self._config.get('device check'):
      swarming_task.wait_for_capacity = True

    assert task.get('xcode build version')
    named_cache = 'xcode_ios_%s' % (task['xcode build version'])
    swarming_task.named_caches[named_cache] = api.ios.XCODE_APP_PATH

    swarming_task.tags.add(
        'device_type:%s' % str(task['test']['device type']))
    swarming_task.tags.add('ios_version:%s' % str(task['test']['os']))
    swarming_task.tags.add('platform:%s' % self._platform)
    swarming_task.tags.add('test:%s' % str(task['test']['app']))

    api.chromium_swarming.trigger_task(swarming_task)
    task['task'] = swarming_task
    self._tasks[suffix] = swarming_task

  @recipe_api.composite_step
  def run(self, api, suffix):
    task = self._task

    assert task['task'], (
        'The task should have been triggered and have an '
        'associated swarming task')

    step_result, has_valid_results = api.chromium_swarming.collect_task(
      task['task'])
    self._suffix_step_name_map[suffix] = '.'.join(step_result.name_tokens)

    # Add any iOS test runner results to the display.
    shard_output_dir = task['task'].get_task_shard_output_dirs()[0]
    test_summary_path = api.path.join(shard_output_dir, 'summary.json')

    if test_summary_path in step_result.raw_io.output_dir:
      test_summary_json = api.json.loads(
          step_result.raw_io.output_dir[test_summary_path])

      logs = test_summary_json.get('logs', {})
      passed_tests = logs.get('passed tests', [])
      flaked_tests = logs.get('flaked tests', [])
      failed_tests = logs.get('failed tests', [])

      # The iOS test runners will not always emit 'failed tests' or any other
      # signal on certain types of errors. This is a test runner bug but we add
      # a workaround here. https:/crbug.com/958791.
      if task['task'].failed_shards and not failed_tests:
        failed_tests = ['invalid test results']

      pass_fail_counts = collections.defaultdict(
          lambda: {'pass_count': 0, 'fail_count': 0})
      for test in passed_tests:
        pass_fail_counts[test]['pass_count'] += 1
      for test in flaked_tests:
        pass_fail_counts[test]['pass_count'] += 1
        pass_fail_counts[test]['fail_count'] += 1
      for test in failed_tests:
        pass_fail_counts[test]['fail_count'] += 1
      test_count = len(passed_tests) + len(flaked_tests) + len(failed_tests)
      canonical_results = api.test_utils.canonical.result_format(
          valid=has_valid_results, failures=failed_tests,
          total_tests_ran=test_count, pass_fail_counts=pass_fail_counts)
      self.update_test_run(api, suffix, canonical_results)

      step_result.presentation.logs['test_summary.json'] = api.json.dumps(
        test_summary_json, indent=2).splitlines()
      step_result.presentation.logs.update(logs)
      step_result.presentation.links.update(
        test_summary_json.get('links', {}))
      if test_summary_json.get('step_text'):
        step_result.presentation.step_text = '%s<br />%s' % (
          step_result.presentation.step_text, test_summary_json['step_text'])
    else:
      self.update_test_run(
          api, suffix, api.test_utils.canonical.result_format())

    # Upload test results JSON to the flakiness dashboard.
    shard_output_dir_full_path = api.path.join(
        task['task'].task_output_dir,
        task['task'].get_task_shard_output_dirs()[0])
    if api.bot_update.last_returned_properties and self._upload_test_results:
      test_results = api.path.join(shard_output_dir_full_path,
                                   'full_results.json')
      if api.path.exists(test_results):
        api.test_results.upload(
          test_results,
          '.'.join(step_result.name_tokens),
          api.bot_update.last_returned_properties.get(
            'got_revision_cp', 'refs/x@{#0}'),
          builder_name_suffix='%s-%s' % (
            task['test']['device type'], task['test']['os']),
          test_results_server='test-results.appspot.com',
        )

    # Upload performance data result to the perf dashboard.
    perf_results_path = api.path.join(
      shard_output_dir, 'Documents', 'perf_result.json')
    if self._result_callback:
      self._result_callback(name=task['test']['app'], step_result=step_result)
    elif perf_results_path in step_result.raw_io.output_dir:
      data = api.json.loads(
          step_result.raw_io.output_dir[perf_results_path])
      data_decode = data['Perf Data']
      data_result = []
      for testcase in data_decode:
        for trace in data_decode[testcase]['value']:
          data_point = api.perf_dashboard.get_skeleton_point(
            'chrome_ios_perf/%s/%s' % (testcase, trace),
            # TODO(huangml): Use revision.
            int(api.time.time()),
            data_decode[testcase]['value'][trace]
          )
          data_point['units'] = data_decode[testcase]['unit']
          data_result.extend([data_point])
      api.perf_dashboard.set_default_config()
      api.perf_dashboard.add_point(data_result)

    return step_result

  def validate_task_results(self, api, step_result):
    raise NotImplementedError()  # pragma: no cover

  def create_task(self, api, suffix, isolated):
    raise NotImplementedError()  # pragma: no cover

  def compile_targets(self):
    raise NotImplementedError()  # pragma: no cover
