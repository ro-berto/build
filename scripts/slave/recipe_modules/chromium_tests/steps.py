# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib
import copy
import datetime
import hashlib
import json
import re
import string
import struct

from recipe_engine.types import freeze


RESULTS_URL = 'https://chromeperf.appspot.com'

# When we retry failing tests, we try to choose a high repeat count so that
# flaky tests will produce both failures and successes. The tradeoff is with
# total run time, which we want to keep low.
REPEAT_COUNT_FOR_FAILING_TESTS = 10


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

  if not (isinstance(test, (SwarmingGTestTest, LocalGTestTest)) or (isinstance(
              test, (SwarmingIsolatedScriptTest, LocalIsolatedScriptTest)) and
              ('webkit_layout_tests' in test.target_name or
               # TODO(crbug.com/914213): Remove webkit_layout_tests reference.
               'blink_web_tests' in test.target_name))):
    # The args that are being merged by this function are only supported
    # by gtest and webkit_layout_tests.
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

  if (test_options_copy.repeat_count is None and
      suffix in ('without patch', 'retry with patch')):
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
  Base class for test suites that can be retried.
  """

  def __init__(self, name, target_name=None, override_isolate_target=None,
               waterfall_mastername=None, waterfall_buildername=None):
    """
    Args:
      waterfall_mastername (str): Matching waterfall buildbot master name.
        This value would be different from trybot master name.
      waterfall_buildername (str): Matching waterfall buildbot builder name.
        This value would be different from trybot builder name.
    """
    super(Test, self).__init__()
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
    self._test_runs = {}
    self._waterfall_mastername = waterfall_mastername
    self._waterfall_buildername = waterfall_buildername
    self._test_options = TestOptions()

    self._name = name
    self._target_name = target_name
    self._override_isolate_target = override_isolate_target

    # Most test suites have a lot of flaky tests. Since we don't rerun passing
    # tests, it's also very easy to introduce new flaky tests. The point of
    # 'retry with patch' is to prevent false rejects by adding another layer of
    # retries. There are two reasons we may want to skip this retry layer.
    #
    # 1) If test-suite layer retries have similar effectiveness to 'retry with
    # patch', then 'retry with patch' may not be necessary,
    # 2) If a test suite has exceptionally few flakes, and there is a
    # sheriffing process to hunt down new flakes as they are introduced, then
    # 'retry with patch' may not be necessary.
    self._should_retry_with_patch = True

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
  def canonical_name(self):
    """Canonical name of the test, no suffix attached."""
    return self.name

  @property
  def isolate_target(self):
    """Returns isolate target name. Defaults to name.
    """
    if self._override_isolate_target:
      return self._override_isolate_target
    return self.target_name

  @property
  def should_retry_with_patch(self):
    return self._should_retry_with_patch

  @property
  def is_gtest(self):
    return False

  @property
  def runs_on_swarming(self):
    return False

  def _create_test_run_invalid_dictionary(self):
    """Returns the dictionary for an invalid test run."""
    return {
      'valid': False,
      'failures': [],
      'total_tests_ran': 0,
      'pass_fail_counts': {},
    }

  def compile_targets(self, api):
    """List of compile targets needed by this test."""
    raise NotImplementedError()  # pragma: no cover

  def pre_run(self, api, suffix):  # pragma: no cover
    """Steps to execute before running the test."""
    del api, suffix
    return []

  def run(self, api, suffix):  # pragma: no cover
    """Run the test.

    suffix is 'with patch', 'without patch' or 'retry with patch'.
    """
    raise NotImplementedError()

  def has_valid_results(self, api, suffix):  # pragma: no cover
    """
    Returns True if results (failures) are valid.

    This makes it possible to distinguish between the case of no failures
    and the test failing to even report its results in machine-readable
    format.
    """
    del api
    if suffix not in self._test_runs:
      return False

    return self._test_runs[suffix]['valid']

  def pass_fail_counts(self, _, suffix):
    """Returns a dictionary of pass and fail counts for each test."""
    return self._test_runs[suffix]['pass_fail_counts']

  def shards_to_retry_with(self, api, original_num_shards, num_tests_to_retry):
    """Calculates the number of shards to run when retrying this test.

    Args:
      api: Recipe api. Used to possibly fail the build, if preconditions aren't
           met.
      original_num_shards: The number of shards used to run the test when it
                           first ran.
      num_tests_to_retry: The number of tests we're trying to retry.

    Returns:
      The number of shards to use when retrying tests that failed.

    Note that this assumes this test has run 'with patch', and knows how many
    tests ran in that case. It doesn't make sense to ask how this test should
    run when retried, if it hasn't run already.
    """
    if not self._test_runs['with patch']['total_tests_ran']: # pragma: no cover
      api.python.failing_step(
        'missing previous run results',
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
                (float(num_tests_to_retry) /
                    self._test_runs['with patch']['total_tests_ran']),
            1),
        original_num_shards), num_tests_to_retry))

  def failures(self, api, suffix):  # pragma: no cover
    """Return tests that failed at least once (list of strings)."""
    if suffix not in self._test_runs:
      api.python.failing_step(
        'cannot find failures for non-existent test run',
        'There is no data for the test run suffix ({0}). This should never '
        'happen as all calls to failures() should first check that the data '
        'exists.'.format(suffix))

    return self._test_runs[suffix]['failures']

  def deterministic_failures(self, api, suffix):
    """Return tests that failed on every test run(list of strings)."""
    if suffix not in self._test_runs: # pragma: no cover
      api.python.failing_step(
        'cannot find deterministic_failures for non-existent test run',
        'There is no data for the test run suffix ({0}). This should never '
        'happen as all calls to deterministic_failures() should first check '
        'that the data exists.'.format(suffix))

    deterministic_failures = []
    for test_name, result in (
        self._test_runs[suffix]['pass_fail_counts'].iteritems()):
      success_count = result['pass_count']
      fail_count = result['fail_count']
      if fail_count > 0 and success_count == 0:
        deterministic_failures.append(test_name)
    return deterministic_failures

  @property
  def uses_isolate(self):
    """Returns true if the test is run via an isolate."""
    return False

  @property
  def uses_local_devices(self):
    return False # pragma: no cover

  def step_name(self, suffix):
    """Helper to uniformly combine tests's name with a suffix."""
    if not suffix:
      return self.name
    return '%s (%s)' % (self.name, suffix)

  def step_metadata(self, api, suffix=None):
    del api
    data = {
        'waterfall_mastername': self._waterfall_mastername,
        'waterfall_buildername': self._waterfall_buildername,
        'canonical_step_name': self.canonical_name,
        'isolate_target_name': self.isolate_target,
    }
    if suffix is not None:
      data['patched'] = suffix in ('with patch', 'retry with patch')
    return data

  def failures_or_invalid_results(self, api, suffix):
    """If results are valid, returns the test failures.

    Returns: A tuple (valid_results, failures).
      valid_results: A Boolean indicating whether results are valid.
      failures: A set of failures. Only valid if valid_results is True.
    """
    if self.has_valid_results(api, suffix):
      # GTestResults.failures is a set whereas TestResults.failures is a dict.
      # In both cases, we want a set.
      return (True, set(self.failures(api, suffix)))
    return (False, None)

  def with_patch_failures(self, api):
    """Returns test failures from the 'with patch' step.

    The 'with_patch' step only considers tests to be failures if every test run
    fails. Flaky tests are considered successes.

    Returns: A tuple (valid_results, failures).
      valid_results: A Boolean indicating whether results are valid.
      failures: A set of strings. Only valid if valid_results is True.
    """
    suffix = 'with patch'
    if self.has_valid_results(api, suffix):
      return (True, set(self.deterministic_failures(api, suffix)))
    return (False, None)

  def without_patch_failures_to_ignore(self, api):
    """Returns test failures that should be ignored.

    Tests that fail in 'without patch' should be ignored, since they're failing
    without the CL patched in.

    Returns: A tuple (valid_results, failures_to_ignore).
      valid_results: A Boolean indicating whether failures_to_ignore is valid.
      failures_to_ignore: A set of strings. Only valid if valid_results is True.
    """
    if not self.has_valid_results(api, 'without patch'):
      return (False, None)

    pass_fail_counts = self.pass_fail_counts(api, 'without patch')
    ignored_failures = set()
    for test_name, results in pass_fail_counts.iteritems():
      # If a test fails at least once, then it's flaky on tip of tree and we
      # should ignore it.
      if results['fail_count'] > 0:
        ignored_failures.add(test_name)
    return (True, ignored_failures)

  def retry_with_patch_successes(self, api):
    """Returns tests that passed in the 'retry with patch' step.

    The 'retry with patch' step only considers tests to be successes if every
    test run passes. Flaky tests are considered failures.

    Returns: A tuple (valid_results, passing_tests).
      valid_results: A Boolean indicating whether results are present and valid.
      passing_tests: A set of strings. Only valid if valid_results is True.
    """
    suffix = 'retry with patch'
    if not self.has_valid_results(api, suffix):
      return (False, None)

    passing_tests = set()
    for test_name, result in (
        self.pass_fail_counts(api, 'retry with patch').iteritems()):
      success_count = result['pass_count']
      fail_count = result['fail_count']
      if fail_count == 0 and success_count > 0:
        passing_tests.add(test_name)
    return (True, passing_tests)

  def tests_to_retry(self, api, suffix):
    """Computes the tests to run on an invocation of the test suite.

    Args:
      suffix: A unique identifier for this test suite invocation. Must be 'with
      patch', 'without patch', or 'retry with patch'.

    Returns:
      A list of tests to retry. Returning None means all tests should be run.
    """
    # For the initial invocation, run every test in the test suite.
    if suffix == 'with patch':
      return None

    # For the second invocation, run previously failing tests.
    # When a patch is adding a new test (and it fails), the test runner is
    # required to just ignore the unknown test.
    if suffix == 'without patch':
      # Invalid results should be treated as if every test failed.
      valid_results, failures = self.failures_or_invalid_results(api,
                                                                 'with patch')
      return sorted(failures) if valid_results else None

    # For the third invocation, run tests that failed in 'with patch', but not
    # in 'without patch'.
    if suffix == 'retry with patch':
      # Invalid results should be treated as if every test failed.
      valid_results, initial_failures = self.failures_or_invalid_results(
          api, 'with patch')
      if not valid_results:
        return None

      # Invalid results without patch should be ignored.
      valid_results, persistent_failures = self.failures_or_invalid_results(
          api, 'without patch')
      if not valid_results:
        persistent_failures = []

      return sorted(set(initial_failures) - set(persistent_failures))

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

  @property
  def should_retry_with_patch(self):
    return self._test.should_retry_with_patch

  def compile_targets(self, api):
    return self._test.compile_targets(api)

  def pre_run(self, api, suffix):
    return self._test.pre_run(api, suffix)

  def run(self, api, suffix):
    return self._test.run(api, suffix)

  def has_valid_results(self, api, suffix):
    return self._test.has_valid_results(api, suffix)

  def failures(self, api, suffix):
    return self._test.failures(api, suffix)

  def deterministic_failures(self, api, suffix):
    return self._test.deterministic_failures(api, suffix)

  def pass_fail_counts(self, api, suffix):
    return self._test.pass_fail_counts(api, suffix)

  @property
  def uses_isolate(self):
    return self._test.uses_isolate

  @property
  def uses_local_devices(self):
    return self._test.uses_local_devices

  def step_metadata(self, api, suffix=None):
    return self._test.step_metadata(api, suffix=suffix)


class ExperimentalTest(TestWrapper):
  """A test wrapper that runs the wrapped test on an experimental test.

  Experimental tests:
    - can run at <= 100%, depending on the experiment_percentage.
    - will not cause the build to fail.
  """

  def __init__(self, test, experiment_percentage):
    super(ExperimentalTest, self).__init__(test)
    self._experiment_percentage = max(0, min(100, int(experiment_percentage)))

  def _experimental_suffix(self, suffix):
    if not suffix:
      return 'experimental'
    return '%s, experimental' % (suffix)

  def _is_in_experiment(self, api):
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


  def _is_in_experiment_and_has_valid_results(self, api, suffix):
    return (self._is_in_experiment(api) and
        super(ExperimentalTest, self).has_valid_results(
            api, self._experimental_suffix(suffix)))

  @property
  def abort_on_failure(self):
    return False

  #override
  def pre_run(self, api, suffix):
    if not self._is_in_experiment(api):
      return []

    try:
      return super(ExperimentalTest, self).pre_run(
          api, self._experimental_suffix(suffix))
    except api.step.StepFailure:
      pass

  #override
  def run(self, api, suffix):
    if not self._is_in_experiment(api):
      return []

    try:
      return super(ExperimentalTest, self).run(
          api, self._experimental_suffix(suffix))
    except api.step.StepFailure:
      pass

  #override
  def has_valid_results(self, api, suffix):
    if self._is_in_experiment(api):
      # Call the wrapped test's implementation in case it has side effects,
      # but ignore the result.
      super(ExperimentalTest, self).has_valid_results(
          api, self._experimental_suffix(suffix))
    return True

  #override
  def failures(self, api, suffix):
    if self._is_in_experiment_and_has_valid_results(api, suffix):
      # Call the wrapped test's implementation in case it has side effects,
      # but ignore the result.
      super(ExperimentalTest, self).failures(
          api, self._experimental_suffix(suffix))
    return []

  #override
  def deterministic_failures(self, api, suffix):
    if self._is_in_experiment_and_has_valid_results(api, suffix):
      # Call the wrapped test's implementation in case it has side effects,
      # but ignore the result.
      super(ExperimentalTest, self).deterministic_failures(
          api, self._experimental_suffix(suffix))
    return []

  def pass_fail_counts(self, api, suffix):
    if self._is_in_experiment_and_has_valid_results(api, suffix):
      # Call the wrapped test's implementation in case it has side effects,
      # but ignore the result.
      super(ExperimentalTest, self).pass_fail_counts(
          api, self._experimental_suffix(suffix))
    return {}


class SizesStep(Test):
  def __init__(self, results_url, perf_id, **kwargs):
    super(SizesStep, self).__init__('sizes', **kwargs)
    self.results_url = results_url
    self.perf_id = perf_id

  def run(self, api, suffix):
    return api.chromium.sizes(self.results_url, self.perf_id)

  def compile_targets(self, _):
    return ['chrome']

  def has_valid_results(self, api, suffix):
    # TODO(sebmarchand): implement this function as well as the
    # |failures| one.
    return True

  def failures(self, api, suffix):
    return []

  def deterministic_failures(self, api, suffix):
    return []

  def pass_fail_counts(self, api, suffix): # pragma: no cover
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

  def compile_targets(self, api):
    if self._override_compile_targets:
      return self._override_compile_targets

    try:
      substitutions = {'name': self._name}

      return [string.Template(s).safe_substitute(substitutions)
              for s in self._all_compile_targets[self._script]]
    except KeyError:  # pragma: no cover
      # There are internal recipes that appear to configure
      # test script steps, but ones that don't have data.
      # We get around this by returning a default value for that case.
      # But the recipes should be updated to not do this.
      # We mark this as pragma: no cover since the public recipes
      # will not exercise this block.
      #
      # TODO(phajdan.jr): Revisit this when all script tests
      # lists move src-side. We should be able to provide
      # test data then.
      if api.chromium._test_data.enabled:
        return []

      raise

  def run(self, api, suffix):
    name = self.name
    if suffix:
      name += ' (%s)' % suffix  # pragma: no cover

    run_args = []

    tests_to_retry = self.tests_to_retry(api, suffix)
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

      failures = result.json.output.get('failures')
      if failures is None:
        self._test_runs[suffix] = self._create_test_run_invalid_dictionary()
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
      self._test_runs[suffix] = {
          'failures': failures,
          'valid': result.json.output['valid'],
          'total_tests_ran': len(failures),
          'pass_fail_counts': pass_fail_counts,
      }

      _, failures = api.test_utils.limit_failures(failures)
      result.presentation.step_text += (
          api.test_utils.format_step_text([
            ['failures:', failures]
          ]))


    return self._test_runs[suffix]


class LocalGTestTest(Test):
  def __init__(self, name, args=None, target_name=None, revision=None,
               webkit_revision=None, android_shard_timeout=None,
               android_tool=None, override_compile_targets=None,
               override_isolate_target=None,
               commit_position_property='got_revision_cp', use_xvfb=True,
               waterfall_mastername=None, waterfall_buildername=None,
               set_up=None, tear_down=None, **runtest_kwargs):
    """Constructs an instance of LocalGTestTest.

    Args:
      name: Displayed name of the test. May be modified by suffixes.
      args: Arguments to be passed to the test.
      target_name: Actual name of the test. Defaults to name.
      revision: Revision of the Chrome checkout.
      webkit_revision: Revision of the WebKit checkout.
      override_compile_targets: List of compile targets for this test
          (for tests that don't follow target naming conventions).
      override_isolate_target: List of isolate targets for this test
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
        name, target_name=target_name,
        override_isolate_target=override_isolate_target,
        waterfall_mastername=waterfall_mastername,
        waterfall_buildername=waterfall_buildername)
    self._args = args or []
    self._target_name = target_name
    self._revision = revision
    self._webkit_revision = webkit_revision
    self._android_shard_timeout = android_shard_timeout
    self._android_tool = android_tool
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

  def compile_targets(self, api):
    # TODO(phajdan.jr): clean up override_compile_targets (remove or cover).
    if self._override_compile_targets:  # pragma: no cover
      return self._override_compile_targets
    return [self.target_name]

  def run(self, api, suffix):
    is_android = api.chromium.c.TARGET_PLATFORM == 'android'
    is_fuchsia = api.chromium.c.TARGET_PLATFORM == 'fuchsia'

    tests_to_retry = self.tests_to_retry(api, suffix)
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
      kwargs['tool'] = self._android_tool
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
        args.extend(['--test_launcher_summary_output', gtest_results_file])
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
      if not hasattr(step_result, 'test_utils'): # pragma: no cover
        self._test_runs[suffix] = self._create_test_run_invalid_dictionary()
      else:
        gtest_results = step_result.test_utils.gtest_results
        self._test_runs[suffix] = gtest_results.canonical_result_format()

      r = api.test_utils.present_gtest_failures(step_result)
      if r:
        self._gtest_results[suffix] = r

        api.test_results.upload(
            api.json.input(r.raw),
            test_type=self.name,
            chrome_revision=api.bot_update.last_returned_properties.get(
                self._commit_position_property, 'x@{#0}'))

    return step_result

  def pass_fail_counts(self, _, suffix):
    if self._gtest_results.get(suffix):
      # test_result exists and is not None.
      return self._gtest_results[suffix].pass_fail_counts
    return {}


class ResultsHandler(object):
  def upload_results(self, api, results, step_name,
                     step_suffix=None):  # pragma: no cover
    """Uploads test results to the Test Results Server.

    Args:
      api: Recipe API object.
      results: Results returned by the step.
      step_name: Name of the step that produced results.
      step_suffix: Suffix appended to the step name.
    """
    raise NotImplementedError()

  def render_results(self, api, results, presentation): # pragma: no cover
    """Renders the test result into the step's output presentation.

    Args:
      api: Recipe API object.
      results: Results returned by the step.
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
    failures.sort()
    num_failures = len(failures)
    if num_failures > cls.MAX_FAILS:
      failures = failures[:cls.MAX_FAILS]
      failures.append('... %d more (%d total) ...' % (
          num_failures - cls.MAX_FAILS, num_failures))
    return ('%s:' % state, ['* %s' % f for f in failures])

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

  def upload_results(self, api, results, step_name, step_suffix=None):
    if hasattr(results, 'as_jsonish'):
      results = results.as_jsonish()

    # Only version 3 of results is supported by the upload server.
    if not results or results.get('version', None) != 3:
      return

    chrome_revision_cp = api.bot_update.last_returned_properties.get(
        'got_revision_cp', 'x@{#0}')
    chrome_revision = str(api.commit_position.parse_revision(
        chrome_revision_cp))
    api.test_results.upload(
      api.json.input(results), chrome_revision=chrome_revision,
      test_type=step_name)

  def render_results(self, api, results, presentation):
    failure_status = (
        api.step.WARNING if self._ignore_task_failure else api.step.FAILURE)
    try:
      results = api.test_utils.create_results_from_json_if_needed(
          results)
    except Exception as e:
      presentation.status = api.step.EXCEPTION
      presentation.step_text += api.test_utils.format_step_text([
          ("Exception while processing test results: %s" % str(e),),
      ])
      presentation.logs['no_results_exc'] = [
          str(e), '\n', api.traceback.format_exc()]
      return

    if not results.valid:
      # TODO(tansell): Change this to api.step.EXCEPTION after discussion.
      presentation.status = failure_status
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
            'Unexpected Failures', results.unexpected_failures.keys()),
    ]
    step_text += [
        self._format_failures(
            'Unexpected Flakes', results.unexpected_flakes.keys()),
    ]
    step_text += [
        self._format_failures(
            'Unexpected Skips', results.unexpected_skipped.keys()),
    ]

    # Unknown test results mean something has probably gone wrong, mark as an
    # exception.
    if results.unknown:
      presentation.status = api.step.EXCEPTION
    step_text += [
        self._format_failures(
            'Unknown test result', results.unknown.keys()),
    ]

    presentation.step_text += api.test_utils.format_step_text(step_text)

  def validate_results(self, api, results):
    try:
      results = api.test_utils.create_results_from_json_if_needed(
          results)
    except Exception as e:
      return False, [str(e), '\n', api.traceback.format_exc()], 0, {}
    # If results were interrupted, we can't trust they have all the tests in
    # them. For this reason we mark them as invalid.
    return (results.valid and not results.interrupted,
            results.unexpected_failures, results.total_test_runs,
            results.pass_fail_counts)


class FakeCustomResultsHandler(ResultsHandler):
  """Result handler just used for testing."""

  def validate_results(self, api, results):
    return True, [], 0, {}

  def render_results(self, api, results, presentation):
    presentation.step_text += api.test_utils.format_step_text([
        ['Fake results data',[]],
    ])
    presentation.links['uploaded'] = 'fake://'

  def upload_results(self, api, results, step_name, step_suffix=None):
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
  def upload_results(self, api, results, step_name, step_suffix=None):
    # Also upload to standard JSON results handler
    JSONResultsHandler.upload_results(
        self, api, results, step_name, step_suffix)

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


class SwarmingTest(Test):
  PRIORITY_ADJUSTMENTS = {
    'higher': -10,
    'normal': 0,
    'lower': +10,
  }

  def __init__(self, name, dimensions=None, target_name=None,
               extra_suffix=None, priority=None, expiration=None,
               hard_timeout=None, io_timeout=None,
               waterfall_mastername=None, waterfall_buildername=None,
               set_up=None, tear_down=None, optional_dimensions=None,
               service_account=None, isolate_coverage_data=None, merge=None,
               ignore_task_failure=None, shards=1,
               **kwargs):
    super(SwarmingTest, self).__init__(
        name, target_name=target_name,
        waterfall_mastername=waterfall_mastername,
        waterfall_buildername=waterfall_buildername,
        **kwargs)
    self._tasks = {}
    self._dimensions = dimensions
    self._optional_dimensions = optional_dimensions
    self._extra_suffix = extra_suffix
    self._priority = priority
    self._expiration = expiration
    self._hard_timeout = hard_timeout
    self._io_timeout = io_timeout
    self._set_up = set_up
    self._merge = merge
    self._tear_down = tear_down
    self._isolate_coverage_data = isolate_coverage_data
    self._ignore_task_failure = ignore_task_failure
    self._shards = shards
    self._service_account = service_account
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
    if os.startswith('Mac'):
      if dimensions.get('hidpi', '') == '1':
        os_name = 'Mac Retina'
      else:
        os_name = 'Mac'
    elif os.startswith('Windows'):
      os_name = 'Windows'
    else:
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
    return self._name

  @property
  def target_name(self):
    return self._target_name or self._name

  @property
  def runs_on_swarming(self):
    return True

  @property
  def shards(self):
    return self._shards

  def create_task(self, api, suffix, isolated_hash):
    """Creates a swarming task. Must be overridden in subclasses.

    Args:
      api: Caller's API.
      suffix: Suffix added to the test name.
      isolated_hash: Hash of the isolated test to be run.

    Returns:
      A SwarmingTask object.
    """
    raise NotImplementedError()  # pragma: no cover

  def _create_task_common(self, api, suffix, isolated_hash, filter_flag,
                          filter_delimiter, task_func):
    # For local tests test_args are added inside api.chromium.runtest.
    args = self._args + api.chromium.c.runtests.test_args

    tests_to_retry = self.tests_to_retry(api, suffix)
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

        shards = self.shards_to_retry_with(api, shards, len(tests_to_retry))

    env = None
    if self._isolate_coverage_data:
      # Targets built with 'use_clang_coverage' will look at this environment
      # variable to determine where to write the profile dumps. The %Nm syntax
      # is understood by this instrumentation, see:
      #   https://clang.llvm.org/docs/SourceBasedCodeCoverage.html#id4
      env = {
          'LLVM_PROFILE_FILE':
              '${ISOLATED_OUTDIR}/profraw/default-%8m.profraw',
      }

      if not self._merge:
        self._merge = api.chromium_tests.m.clang_coverage.shard_merge(
            self.step_name(suffix))

    task = task_func(
        build_properties=api.chromium.build_properties,
        cipd_packages=self._cipd_packages,
        env=env,
        extra_args=args,
        ignore_task_failure=self._ignore_task_failure,
        isolated_hash=isolated_hash,
        merge=self._merge,
        shards=shards,
        title=self.step_name(suffix),
        trigger_script=self._trigger_script,
        service_account=self._service_account,
    )

    if self._priority in self.PRIORITY_ADJUSTMENTS:
      task.priority += self.PRIORITY_ADJUSTMENTS[self._priority]

    if self._expiration:
      task.expiration = self._expiration

    if self._hard_timeout:
      task.hard_timeout = self._hard_timeout

    if self._io_timeout:
      task.io_timeout = self._io_timeout

    # Add custom dimensions.
    if self._dimensions:  # pragma: no cover
      #TODO(stip): concoct a test case that will trigger this codepath
      for k, v in self._dimensions.iteritems():
         if v is None:
           # Remove key if it exists. This allows one to use None to remove
           # default dimensions.
           task.dimensions.pop(k, None)
         else:
           task.dimensions[k] = v

    # Add optional dimensions.
    if self._optional_dimensions:
        task.optional_dimensions = self._optional_dimensions

    # Set default value.
    if 'os' not in task.dimensions:
      task.dimensions['os'] = api.swarming.prefered_os_dimension(
          api.platform.name)

    return task

  def get_task(self, suffix):
    return self._tasks.get(suffix)

  def pre_run(self, api, suffix):
    """Launches the test on Swarming."""
    assert suffix not in self._tasks, (
        'Test %s was already triggered' % self.step_name(suffix))

    # *.isolated may be missing if *_run target is misconfigured. It's a error
    # in gyp, not a recipe failure. So carry on with recipe execution.
    isolated_hash = api.isolate.isolated_tests.get(self.isolate_target)
    if not isolated_hash:
      return api.python.failing_step(
          '[error] %s' % self.step_name(suffix),
          '*.isolated file for target %s is missing' % self.isolate_target)

    # Create task.
    self._tasks[suffix] = self.create_task(api, suffix, isolated_hash)

    return api.swarming.trigger_task(self._tasks[suffix])

  def validate_task_results(self, api, step_result):
    """Interprets output of a task (provided as StepResult object).

    Called for successful and failed tasks.

    Args:
      api: Caller's API.
      step_result: StepResult object to examine.

    Returns:
      A tuple (valid, failures, total_tests_ran, pass_fail_counts), where:
        * valid is True if valid results are available
        * failures is a list of names of failed tests (ignored if valid is
            False).
        * total_tests_ran counts the number of tests executed.
        * pass_fail_counts is a dictionary that includes the number of passes
            and fails for each test.
    """
    raise NotImplementedError()  # pragma: no cover

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

    try:
      api.swarming.collect_task(self._tasks[suffix])
    finally:
      step_result = api.step.active_result

      step_result.presentation.logs['step_metadata'] = (
          json.dumps(self.step_metadata(api, suffix), sort_keys=True,
                     indent=2)
      ).splitlines()

      valid, failures, total_tests_ran, pass_fail_counts = (
          self.validate_task_results(api, step_result))
      self._test_runs[suffix] = {
          'valid': valid,
          'failures': failures,
          'total_tests_ran': total_tests_ran,
          'pass_fail_counts': pass_fail_counts
      }

      if step_result.retcode == 0 and not valid:
        # This failure won't be caught automatically. Need to manually
        # raise it as a step failure.
        raise api.step.StepFailure(api.test_utils.INVALID_RESULTS_MAGIC)

  @property
  def uses_isolate(self):
    return True

  def step_metadata(self, api, suffix=None):
    data = super(SwarmingTest, self).step_metadata(api, suffix)
    if suffix is not None:
      data['full_step_name'] = api.swarming.get_step_name(
          prefix=None, task=self._tasks[suffix])
      data['patched'] = suffix in ('with patch', 'retry with patch')
      data['dimensions'] = self._tasks[suffix].dimensions
      data['swarm_task_ids'] = self._tasks[suffix].get_task_ids()
    return data


class SwarmingGTestTest(SwarmingTest):
  def __init__(self, name, args=None, target_name=None, shards=1,
               dimensions=None, extra_suffix=None, priority=None,
               expiration=None, hard_timeout=None, io_timeout=None,
               override_compile_targets=None, override_isolate_target=None,
               cipd_packages=None, waterfall_mastername=None,
               waterfall_buildername=None, merge=None, trigger_script=None,
               set_up=None, tear_down=None, isolate_coverage_data=False,
               optional_dimensions=None, service_account=None):
    super(SwarmingGTestTest, self).__init__(
        name, dimensions, target_name, extra_suffix, priority, expiration,
        hard_timeout, io_timeout, waterfall_mastername=waterfall_mastername,
        waterfall_buildername=waterfall_buildername,
        set_up=set_up, tear_down=tear_down,
        override_isolate_target=override_isolate_target,
        isolate_coverage_data=isolate_coverage_data,
        merge=merge, shards=shards,
        optional_dimensions=optional_dimensions,
        service_account=service_account)
    self._args = args or []
    self._override_compile_targets = override_compile_targets
    self._cipd_packages = cipd_packages
    self._gtest_results = {}
    self._trigger_script = trigger_script

  @Test.test_options.setter
  def test_options(self, value):
    self._test_options = value

  @property
  def is_gtest(self):
    return True

  def compile_targets(self, api):
    if self._override_compile_targets:
      return self._override_compile_targets
    return [self.target_name]

  def create_task(self, api, suffix, isolated_hash):
    def _create_swarming_task(*args, **kwargs):
      kwargs['test_launcher_summary_output'] = (
          api.test_utils.gtest_results(add_json_log=False))
      return api.swarming.gtest_task(*args, **kwargs)

    return self._create_task_common(
        api, suffix, isolated_hash, '--gtest_filter', ':',
        _create_swarming_task)

  def validate_task_results(self, api, step_result):
    if not hasattr(step_result, 'test_utils'):
      return False, None, 0, None  # pragma: no cover

    gtest_results = step_result.test_utils.gtest_results
    if not gtest_results:
      return False, None, 0, None  # pragma: no cover

    global_tags = gtest_results.raw.get('global_tags', [])
    if 'UNRELIABLE_RESULTS' in global_tags:
      return False, None, 0, None  # pragma: no cover

    return (gtest_results.valid, gtest_results.failures,
            gtest_results.total_tests_ran, gtest_results.pass_fail_counts)

  def pass_fail_counts(self, _, suffix):
    if self._gtest_results.get(suffix):
      # test_result exists and is not None.
      return self._gtest_results[suffix].pass_fail_counts
    return {}

  def run(self, api, suffix):
    """Waits for launched test to finish and collects the results."""
    try:
      super(SwarmingGTestTest, self).run(api, suffix)
    finally:
      step_result = api.step.active_result
      if (hasattr(step_result, 'test_utils') and
          hasattr(step_result.test_utils, 'gtest_results')):
        gtest_results = getattr(step_result.test_utils, 'gtest_results', None)
        self._gtest_results[suffix] = gtest_results
        # Only upload test results if we have gtest results.
        if gtest_results and gtest_results.raw:
          parsed_gtest_data = gtest_results.raw
          chrome_revision_cp = api.bot_update.last_returned_properties.get(
              'got_revision_cp', 'x@{#0}')
          chrome_revision = str(api.commit_position.parse_revision(
              chrome_revision_cp))
          api.test_results.upload(
              api.json.input(parsed_gtest_data),
              chrome_revision=chrome_revision,
              test_type=step_result.step['name'])


class LocalIsolatedScriptTest(Test):
  def __init__(self, name, args=None, target_name=None,
               override_compile_targets=None, results_handler=None,
               set_up=None, tear_down=None, isolate_coverage_data=None,
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
    self._test_results = {}
    self._isolate_coverage_data = isolate_coverage_data

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

  def compile_targets(self, _):
    if self._override_compile_targets:
      return self._override_compile_targets
    return [self.target_name]

  def pass_fail_counts(self, _, suffix):
    if self._test_results.get(suffix):
      # test_result exists and is not None.
      return self._test_results[suffix].pass_fail_counts
    return {}

  @Test.test_options.setter
  def test_options(self, value):
    self._test_options = value

  # TODO(nednguyen, kbr): figure out what to do with Android.
  # (crbug.com/533480)
  def run(self, api, suffix):
    tests_to_retry = self.tests_to_retry(api, suffix)
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
    if self._isolate_coverage_data:
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
      results = step_result.json.output
      presentation = step_result.presentation
      valid, _, _, _ = self.results_handler.validate_results(api, results)
      test_results = (api.test_utils.create_results_from_json_if_needed(
          results) if valid else None)
      self._test_results[suffix] = test_results

      self.results_handler.render_results(api, results, presentation)

      if valid:
        self._test_runs[suffix] = test_results.canonical_result_format()
      else:
        self._test_runs[suffix] = self._create_test_run_invalid_dictionary()

      if api.step.active_result.retcode == 0 and not valid:
        # This failure won't be caught automatically. Need to manually
        # raise it as a step failure.
        raise api.step.StepFailure(api.test_utils.INVALID_RESULTS_MAGIC)

    return self._test_runs[suffix]


class SwarmingIsolatedScriptTest(SwarmingTest):

  def __init__(self, name, args=None, target_name=None, shards=1,
               dimensions=None, extra_suffix=None,
               ignore_task_failure=False, priority=None, expiration=None,
               hard_timeout=None, override_compile_targets=None, perf_id=None,
               results_url=None, perf_dashboard_id=None, io_timeout=None,
               waterfall_mastername=None, waterfall_buildername=None,
               merge=None, trigger_script=None, results_handler=None,
               set_up=None, tear_down=None, idempotent=True,
               cipd_packages=None, isolate_coverage_data=False,
               optional_dimensions=None, service_account=None):
    super(SwarmingIsolatedScriptTest, self).__init__(
        name, dimensions, target_name, extra_suffix, priority, expiration,
        hard_timeout, io_timeout, waterfall_mastername=waterfall_mastername,
        waterfall_buildername=waterfall_buildername,
        set_up=set_up, tear_down=tear_down,
        isolate_coverage_data=isolate_coverage_data,
        merge=merge, shards=shards,
        ignore_task_failure=ignore_task_failure,
        optional_dimensions=optional_dimensions,
        service_account=service_account)
    self._args = args or []
    self._override_compile_targets = override_compile_targets
    self._perf_id=perf_id
    self._results_url = results_url
    self._perf_dashboard_id = perf_dashboard_id
    self._isolated_script_results = {}
    self._trigger_script = trigger_script
    self.results_handler = results_handler or JSONResultsHandler(
        ignore_task_failure=ignore_task_failure)
    self._test_results = {}
    self._idempotent = idempotent
    self._cipd_packages = cipd_packages

  @property
  def target_name(self):
    return self._target_name or self._name

  def compile_targets(self, _):
    if self._override_compile_targets:
      return self._override_compile_targets
    return [self.target_name]

  @property
  def uses_isolate(self):
    return True

  @Test.test_options.setter
  def test_options(self, value):
    self._test_options = value

  def create_task(self, api, suffix, isolated_hash):
    def _create_swarming_task(*args, **kwargs):
      # For the time being, we assume all isolated_script_test are not
      # idempotent TODO(crbug.com/549140): remove the self._idempotent
      # parameter once Telemetry tests are idempotent, since that will make all
      # isolated_script_tests idempotent.
      kwargs['idempotent'] = self._idempotent
      return api.swarming.isolated_script_task(*args, **kwargs)

    return self._create_task_common(
        api, suffix, isolated_hash, '--isolated-script-test-filter', '::',
        _create_swarming_task)

  def pass_fail_counts(self, _, suffix):
    if self._test_results.get(suffix):
      # test_result exists and is not None.
      return self._test_results[suffix].pass_fail_counts
    return {}

  def validate_task_results(self, api, step_result):
    # If we didn't get a step_result object at all, we can safely
    # assume that something definitely went wrong.
    if step_result is None:  # pragma: no cover
      return False, None, 0, {}

    results = getattr(step_result, 'isolated_script_results', None) or {}

    global_tags = results.get('global_tags', [])
    if 'UNRELIABLE_RESULTS' in global_tags:
      return False, None, 0, {}

    valid, failures, total_tests_ran, pass_fail_counts = (
        self.results_handler.validate_results(api, results))
    presentation = step_result.presentation
    self.results_handler.render_results(api, results, presentation)

    self._isolated_script_results = results

    # If we got no results and a nonzero exit code, the test probably
    # did not run correctly.
    if step_result.retcode != 0 and not results:
      return False, failures, total_tests_ran, {}

    # Even if the output is valid, if the return code is greater than
    # MAX_FAILURES_EXIT_STATUS then the test did not complete correctly and the
    # results can't be trusted. It probably exited early due to a large number
    # of failures or an environment setup issue.
    if step_result.retcode > api.test_utils.MAX_FAILURES_EXIT_STATUS:
      return False, failures, total_tests_ran, {}

    if step_result.retcode == 0 and not valid:
      # This failure won't be caught automatically. Need to manually
      # raise it as a step failure.
      raise api.step.StepFailure(api.test_utils.INVALID_RESULTS_MAGIC)

    return valid, failures, total_tests_ran, pass_fail_counts

  def run(self, api, suffix):
    try:
      super(SwarmingIsolatedScriptTest, self).run(api, suffix)
    finally:
      results = self._isolated_script_results

      if self._test_runs.get(suffix, {}).get('valid'):
        self._test_results[suffix] = (
            api.test_utils.create_results_from_json_if_needed(results))

      if results:
        self.results_handler.upload_results(
            api, results, self.step_name(suffix), suffix)


class PythonBasedTest(Test):
  def __init__(self, name, **kwargs):
    super(PythonBasedTest, self).__init__(name, **kwargs)

  def compile_targets(self, _):
    return []  # pragma: no cover

  def run_step(self, api, suffix, cmd_args, **kwargs):
    raise NotImplementedError()  # pragma: no cover

  def run(self, api, suffix):
    # These arguments must be passed to an invocation of the recipe engine. The
    # recipe engine will recognize that the second argument is a subclass of
    # OutputPlaceholder and use that to populate
    # step_result.test_utils.test_results.
    cmd_args = ['--write-full-results-to',
                api.test_utils.test_results(add_json_log=False)]
    tests_to_retry = self.tests_to_retry(api, suffix)
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
    test_results = step_result.test_utils.test_results
    presentation = step_result.presentation

    if (test_results.valid and
        step_result.retcode <= api.test_utils.MAX_FAILURES_EXIT_STATUS):
      self._test_runs[suffix] = test_results.canonical_result_format()
      _, failures = api.test_utils.limit_failures(
          test_results.unexpected_failures.keys())
      presentation.step_text += api.test_utils.format_step_text([
          ['unexpected_failures:', failures],
      ])
      if failures:
        presentation.status = api.step.FAILURE
    else:
      self._test_runs[suffix] = self._create_test_run_invalid_dictionary()
      presentation.status = api.step.EXCEPTION
      presentation.step_text = api.test_utils.INVALID_RESULTS_MAGIC

    return step_result


class BisectTest(Test):
  def __init__(self, test_parameters=None, **kwargs):
    if not test_parameters:
      test_parameters = {}
    super(BisectTest, self).__init__('bisect_test')
    self._test_parameters = test_parameters
    self.run_results = {}
    self.kwargs = kwargs
    self.test_config = None

  @property
  def abort_on_failure(self):
    return True  # pragma: no cover

  @property
  def uses_local_devices(self):
    return False

  def compile_targets(self, _):  # pragma: no cover
    return ['chrome'] # Bisect always uses a separate bot for building.

  def pre_run(self, api, _):
    self.test_config = api.bisect_tester.load_config_from_dict(
        self._test_parameters.get('bisect_config',
                                  api.properties.get('bisect_config')))

  def run(self, api, suffix):
    self.run_results = api.bisect_tester.run_test(
        self.test_config, **self.kwargs)
    self._test_runs[suffix] = self._create_test_run_invalid_dictionary()
    self._test_runs[suffix]['valid'] = bool(self.run_results.get('retcodes'))


class BisectTestStaging(Test):
  def __init__(self, test_parameters=None, **kwargs):
    if not test_parameters:
      test_parameters = {}
    super(BisectTestStaging, self).__init__('bisect test staging')
    self._test_parameters = test_parameters
    self.run_results = {}
    self.kwargs = kwargs
    self.test_config = None

  @property
  def abort_on_failure(self):
    return True  # pragma: no cover

  @property
  def uses_local_devices(self):
    return False

  def compile_targets(self, _):  # pragma: no cover
    return ['chrome'] # Bisect always uses a separate bot for building.

  def pre_run(self, api, _):
    self.test_config = api.bisect_tester_staging.load_config_from_dict(
        self._test_parameters.get('bisect_config',
                                  api.properties.get('bisect_config')))

  def run(self, api, suffix):
    self.run_results = api.bisect_tester_staging.run_test(
        self.test_config, **self.kwargs)
    self._test_runs[suffix] = self._create_test_run_invalid_dictionary()
    self._test_runs[suffix]['valid'] = bool(self.run_results.get('retcodes'))


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

  def run(self, api, suffix):
    assert api.chromium.c.TARGET_PLATFORM == 'android'

    json_results_file = api.test_utils.gtest_results(add_json_log=False)
    try:
      step_result = self.run_tests(api, suffix, json_results_file)
    except api.step.StepFailure as f:
      step_result = f.result
      raise
    finally:
      self._test_runs[suffix] = self._create_test_run_invalid_dictionary()
      presentation_step = api.python.succeeding_step(
          'Report %s results' % self.name, '')
      gtest_results = api.test_utils.present_gtest_failures(
          step_result, presentation=presentation_step.presentation)
      if gtest_results:
        self._test_runs[suffix] = gtest_results.canonical_result_format()

        api.test_results.upload(
            api.json.input(gtest_results.raw),
            test_type=step_result.step['name'],
            chrome_revision=api.bot_update.last_returned_properties.get(
                'got_revision_cp', 'x@{#0}'))

  def compile_targets(self, _):
    return self._compile_targets


class AndroidJunitTest(AndroidTest):
  def __init__(
      self, name, waterfall_mastername=None, waterfall_buildername=None):
    super(AndroidJunitTest, self).__init__(
        name, compile_targets=[name], waterfall_mastername=None,
        waterfall_buildername=None)

  @property
  def uses_local_devices(self):
    return False

  #override
  def run_tests(self, api, suffix, json_results_file):
    return api.chromium_android.run_java_unit_test_suite(
        self.name, verbose=True, suffix=suffix,
        json_results_file=json_results_file,
        step_test_data=lambda: api.test_utils.test_api.canned_gtest_output(
            False))


class AndroidInstrumentationTest(AndroidTest):
  _DEFAULT_SUITES = {
    'ChromePublicTest': {
      'compile_target': 'chrome_public_test_apk',
    },
    'ChromotingTest': {
      'compile_target': 'remoting_test_apk',
    },
    'ContentShellTest': {
      'compile_target': 'content_shell_test_apk',
    },
    'MojoTest': {
      'compile_target': 'mojo_test_apk',
    },
    'SystemWebViewShellLayoutTest': {
      'compile_target': 'system_webview_shell_layout_test_apk',
    },
    'WebViewInstrumentationTest': {
      'compile_target': 'webview_instrumentation_test_apk',
    },
    'WebViewUiTest': {
      'compile_target': 'webview_ui_test_app_test_apk',
      # TODO(yolandyan): These should be removed once crbug/643660 is resolved
      'additional_compile_targets': [
        'system_webview_apk',
      ],
      'additional_apks': [
        'SystemWebView.apk',
      ],
    }
  }

  _DEFAULT_SUITES_BY_TARGET = {
    'chrome_public_test_apk': _DEFAULT_SUITES['ChromePublicTest'],
    'content_shell_test_apk': _DEFAULT_SUITES['ContentShellTest'],
    'mojo_test_apk': _DEFAULT_SUITES['MojoTest'],
    'remoting_test_apk': _DEFAULT_SUITES['ChromotingTest'],
    'system_webview_shell_layout_test_apk':
        _DEFAULT_SUITES['SystemWebViewShellLayoutTest'],
    'webview_instrumentation_test_apk':
        _DEFAULT_SUITES['WebViewInstrumentationTest'],
    'webview_ui_test_app_test_apk': _DEFAULT_SUITES['WebViewUiTest'],
  }

  def __init__(self, name, compile_targets=None, apk_under_test=None,
               test_apk=None, timeout_scale=None, annotation=None,
               except_annotation=None, screenshot=False, verbose=True,
               tool=None, additional_apks=None, store_tombstones=False,
               trace_output=False, result_details=False, args=None,
               waterfall_mastername=None, waterfall_buildername=None,
               target_name=None, set_up=None, tear_down=None):
    suite_defaults = (
        AndroidInstrumentationTest._DEFAULT_SUITES.get(name)
        or AndroidInstrumentationTest._DEFAULT_SUITES_BY_TARGET.get(name)
        or {})
    if not compile_targets:
      compile_targets = [
          suite_defaults.get('compile_target', target_name or name)]
      compile_targets.extend(
          suite_defaults.get('additional_compile_targets', []))

    super(AndroidInstrumentationTest, self).__init__(
        name,
        compile_targets,
        waterfall_mastername=waterfall_mastername,
        waterfall_buildername=waterfall_buildername)
    self._additional_apks = (
        additional_apks or suite_defaults.get('additional_apks'))
    self._annotation = annotation
    self._apk_under_test = (
        apk_under_test or suite_defaults.get('apk_under_test'))
    self._except_annotation = except_annotation
    self._screenshot = screenshot
    self._test_apk = test_apk or suite_defaults.get('test_apk')
    self._timeout_scale = timeout_scale
    self._tool = tool
    self._verbose = verbose
    self._wrapper_script_suite_name = compile_targets[0]
    self._trace_output = trace_output
    self._store_tombstones = store_tombstones
    self._result_details = result_details
    self._args = args
    self._set_up = set_up
    self._tear_down = tear_down

  @property
  def set_up(self):
    return self._set_up

  @property
  def tear_down(self):
    return self._tear_down

  @property
  def uses_local_devices(self):
    return True

  #override
  def run_tests(self, api, suffix, json_results_file):
    return api.chromium_android.run_instrumentation_suite(
        self.name,
        test_apk=api.chromium_android.apk_path(self._test_apk),
        apk_under_test=api.chromium_android.apk_path(self._apk_under_test),
        additional_apks=[
            api.chromium_android.apk_path(a)
            for a in self._additional_apks or []],
        suffix=suffix,
        annotation=self._annotation, except_annotation=self._except_annotation,
        screenshot=self._screenshot, verbose=self._verbose, tool=self._tool,
        json_results_file=json_results_file,
        timeout_scale=self._timeout_scale,
        result_details=self._result_details,
        store_tombstones=self._store_tombstones,
        wrapper_script_suite_name=self._wrapper_script_suite_name,
        trace_output=self._trace_output,
        step_test_data=lambda: api.test_utils.test_api.canned_gtest_output(
            False),
        args=self._args)


class BlinkTest(Test):
  # TODO(dpranke): This should be converted to a PythonBasedTest, although it
  # will need custom behavior because we archive the results as well.
  def __init__(self, extra_args=None):
    super(BlinkTest, self).__init__('blink_web_tests')
    self._extra_args = extra_args
    self.results_handler = LayoutTestResultsHandler()

  def compile_targets(self, api):
    return ['blink_tests']

  @property
  def uses_local_devices(self):
    return True

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

    tests_to_retry = self.tests_to_retry(api, suffix)
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

      # TODO(dpranke): crbug.com/357866 - note that all comparing against
      # MAX_FAILURES_EXIT_STATUS tells us is that we did not exit early
      # or abnormally; it does not tell us how many failures there actually
      # were, which might be much higher (up to 5000 diffs, where we
      # would bail out early with --exit-after-n-failures) or lower
      # if we bailed out after 100 crashes w/ -exit-after-n-crashes, in
      # which case the retcode is actually 130
      if step_result.retcode > api.test_utils.MAX_FAILURES_EXIT_STATUS:
        self._test_runs[suffix] = self._create_test_run_invalid_dictionary()
      else:
        self._test_runs[suffix] = (step_result.test_utils.test_results.
            canonical_result_format())

      if step_result:
        results = step_result.test_utils.test_results

        self.results_handler.render_results(
            api, results, step_result.presentation)

        self.results_handler.upload_results(api, results, step_name, suffix)


class MiniInstallerTest(PythonBasedTest):  # pylint: disable=W0232
  def __init__(self, **kwargs):
    super(MiniInstallerTest, self).__init__('test_installer', **kwargs)

  def compile_targets(self, _):
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


class WebViewCTSTest(AndroidTest):

  def __init__(self, platform, arch, command_line_args=None,
               waterfall_mastername=None, waterfall_buildername=None):
    super(WebViewCTSTest, self).__init__(
        'WebView CTS: %s' % platform,
        ['system_webview_apk'],
        waterfall_mastername,
        waterfall_buildername)
    self._arch = arch
    self._command_line_args = command_line_args
    self._platform = platform

  @property
  def uses_local_devices(self):
    return True

  def run_tests(self, api, suffix, json_results_file):
    api.chromium_android.adb_install_apk(
        api.chromium_android.apk_path('SystemWebView.apk'))
    return api.chromium_android.run_webview_cts(
        android_platform=self._platform,
        suffix=suffix,
        command_line_args=self._command_line_args,
        arch=self._arch,
        json_results_file=json_results_file,
        result_details=True)


class IncrementalCoverageTest(Test):
  def __init__(self, **kwargs):
    super(IncrementalCoverageTest, self).__init__(
        'incremental coverage', **kwargs)

  @property
  def uses_local_devices(self):
    return True

  def has_valid_results(self, api, suffix):
    return True

  def failures(self, api, suffix):
    return []

  def pass_fail_counts(self, api, suffix): # pragma: no cover
    return {}

  def compile_targets(self, api):
    """List of compile targets needed by this test."""
    return []

  def run(self, api, suffix):
    api.chromium_android.coverage_report(upload=False)
    api.chromium_android.get_changed_lines_for_revision()
    api.chromium_android.incremental_coverage_report()

class FindAnnotatedTest(Test):
  _TEST_APKS = {
      'chrome_public_test_apk': 'ChromePublicTest',
      'content_shell_test_apk': 'ContentShellTest',
      'system_webview_shell_layout_test_apk': 'SystemWebViewShellLayoutTest',
      'webview_instrumentation_test_apk': 'WebViewInstrumentationTest',
  }

  def __init__(self, **kwargs):
    super(FindAnnotatedTest, self).__init__('Find annotated test', **kwargs)

  def compile_targets(self, api):
    return FindAnnotatedTest._TEST_APKS.keys()

  def run(self, api, suffix):
    with api.tempfile.temp_dir('annotated_tests_json') as temp_output_dir:
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
        api.python(
            'run find_annotated_tests.py',
            api.path['checkout'].join(
                'tools', 'android', 'find_annotated_tests.py'),
            args=args)
      api.gsutil.upload(
          temp_output_dir.join(
              '%s-android-chrome.json' % timestamp_string),
          'chromium-annotated-tests', 'android')


class WebRTCPerfTest(LocalGTestTest):
  """A LocalGTestTest reporting perf metrics.

  WebRTC is the only project that runs correctness tests with perf reporting
  enabled at the same time, which differs from the chromium.perf bots.
  """
  def __init__(self, name, args, perf_id, perf_config_mappings,
               commit_position_property, **runtest_kwargs):
    """Construct a WebRTC Perf test.

    Args:
      name: Name of the test.
      args: Command line argument list.
      perf_id: String identifier (preferably unique per machine).
      perf_config_mappings: A dict that maps revision keys to be put in the perf
        config to revision properties coming from the bot_update step.
      commit_position_property: Commit position property for the Chromium
        checkout. It's needed because for chromium.webrtc.fyi 'got_revision_cp'
        refers to WebRTC's commit position instead of Chromium's, so we have to
        use 'got_cr_revision_cp' instead.
    """
    assert perf_id
    self._perf_config_mappings = perf_config_mappings or {}
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

  def run(self, api, suffix):
    self._wire_up_perf_config(api)
    super(WebRTCPerfTest, self).run(api, suffix)

  def _wire_up_perf_config(self, api):
    props = api.bot_update.last_returned_properties
    perf_config = { 'a_default_rev': 'r_webrtc_git' }

    for revision_key, revision_prop in self._perf_config_mappings.iteritems():
      perf_config[revision_key] = props[revision_prop]

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

  def __init__(self, name='MockTest', target_name=None,
               waterfall_mastername=None, waterfall_buildername=None,
               abort_on_failure=False, has_valid_results=True, failures=None):
    super(MockTest, self).__init__(waterfall_mastername, waterfall_buildername)
    self._target_name = target_name
    self._abort_on_failure = abort_on_failure
    self._failures = failures or []
    self._has_valid_results = has_valid_results
    self._name = name

  @property
  def name(self):
    return self._name

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

  def run(self, api, suffix):
    with self._mock_exit_codes(api):
      api.step('%s%s' % (self.name, self._mock_suffix(suffix)), None)

  def has_valid_results(self, api, suffix):
    api.step(
        'has_valid_results %s%s' % (self.name, self._mock_suffix(suffix)), None)
    return self._has_valid_results

  def failures(self, api, suffix):
    api.step('failures %s%s' % (self.name, self._mock_suffix(suffix)), None)
    return self._failures

  def deterministic_failures(self, api, suffix):
    """Use same logic as failures for the Mock test."""
    return self.failures(api, suffix)

  def pass_fail_counts(self, _, suffix):
    return {}

  def compile_targets(self, api): # pragma: no cover
    del api
    return []

  @property
  def abort_on_failure(self):
    return self._abort_on_failure


class MockSwarmingTest(SwarmingIsolatedScriptTest, MockTest):
  pass
