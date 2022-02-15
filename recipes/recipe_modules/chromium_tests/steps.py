# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Classes for running different kinds of tests.

This module contains two main class hierarchies: test specs and tests.
Test specs are immutable objects that define the details of a specific
test and can be used to create the test object, which actually knows how
to execute a test. Test objects can also be decorated with test
wrappers, which can modify the execution of the test.

The class `TestSpecBase` is the root of the class hierarchy for test
specs and test wrapper specs. It defines the single method `get_test`
which is how the test or wrapped test is obtained from the spec.

All test spec types inherit from `TestSpec`. `TestSpec` implements the
`get_test` method in terms of the `test_class` property, which concrete
subclasses must override to return the class of the test type. All test
wrapper types inherit from `TestWrapperSpec`.`TestWrapperSpec`
implements the `get_test` method in terms of the `test_wrapper_class`
property, which concrete subclasses must override to return the class of
the test wrapper type.

The class `Test` is the root of the class hierarchy for tests and test
wrappers. All test types inherit from `Test` and all test wrapper types
inherit from `TestWrapper`, which are both abstract base classes. Each
concrete test type or test wrapper type has an associated spec type that
contains the input details for the test or test wrapper and is the only
argument to the __init__ method of the test type or test wrapper type.
"""

import abc
import attr
import collections
import contextlib
import copy
import hashlib
import re
import six
import string
import struct
from six.moves import urllib

from recipe_engine import recipe_api
from recipe_engine.config_types import Path
from recipe_engine.engine_types import freeze

from .resultdb import ResultDB

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2
from PB.go.chromium.org.luci.resultdb.proto.v1 import (test_result as
                                                       test_result_pb2)

from RECIPE_MODULES.build import chromium_swarming
from RECIPE_MODULES.build.skylab.structs import SkylabRequest
from RECIPE_MODULES.build.attr_utils import (attrib, attrs, cached_property,
                                             callable_, command_args, enum,
                                             mapping, sequence)

RESULTS_URL = 'https://chromeperf.appspot.com'

# When we retry failing tests, we try to choose a high repeat count so that
# flaky tests will produce both failures and successes. The tradeoff is with
# total run time, which we want to keep low.
REPEAT_COUNT_FOR_FAILING_TESTS = 10

# Pinned version of
# https://chromium.googlesource.com/infra/infra/+/main/go/src/infra/cmd/mac_toolchain
MAC_TOOLCHAIN_PACKAGE = 'infra/tools/mac_toolchain/${platform}'
MAC_TOOLCHAIN_VERSION = (
    'git_revision:723fc1a6c8cdf2631a57851f5610e598db0c1de1')
MAC_TOOLCHAIN_ROOT = '.'

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

ALLOWED_RESULT_HANDLER_NAMES = ('default', 'layout tests', 'fake')

# Matches the name of the new invocation that gets printed to stderr when
# calling `rdb stream -new`.
RDB_INVOCATION_NAME_RE = re.compile(r'rdb-stream: included "(\S+)" in "\S+"')

INCLUDE_CI_FOOTER = 'Include-Ci-Only-Tests'


class TestOptions(object):
  """Abstracts command line flags to be passed to the test."""

  def __init__(self,
               repeat_count=None,
               test_filter=None,
               run_disabled=False,
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


def _supports_test_arguments(test):
  if isinstance(test, (SwarmingGTestTest, LocalGTestTest)):
    return True
  if (isinstance(test,
                 (SwarmingIsolatedScriptTest, LocalIsolatedScriptTest)) and
      'blink_web_tests' in test.target_name):
    return True

  return (test.api.m.chromium.c and
          test.api.m.chromium.c.TARGET_PLATFORM == 'ios')


def _merge_args_and_test_options(test, args, options):
  """Adds args from test options.

  Args:
    test: A test suite. An instance of a subclass of Test.
    args: The list of args of extend.
    options: The TestOptions to use to extend args.
    api: An api object providing access to Chromium configs

  Returns:
    The extended list of args.
  """
  args = list(args)

  if not _supports_test_arguments(test):
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


def _add_suffix(step_name, suffix):
  if not suffix:
    return step_name
  return '{} ({})'.format(step_name, suffix)


def _present_info_messages(presentation, test):
  messages = list(test.spec.info_messages)
  messages.append(presentation.step_text)
  presentation.step_text = '\n'.join(messages)


class DisabledReason(object):
  """Abstract base class for identifying why a test is disabled."""

  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def report_tests(self, chromium_tests_api, tests):
    """Report tests that are disabled for this reason."""
    raise NotImplementedError()  # pragma: no cover


class _CiOnly(DisabledReason):
  """Identifies a ci_only test that is disabled on try."""

  def report_tests(self, chromium_tests_api, tests):
    result = chromium_tests_api.m.step('ci_only tests', [])
    message = [('The following tests are not being run on this try builder'
                ' because they are marked \'ci_only\', adding "{}: true"'
                ' to the gerrit footers will cause them to run'
               ).format(INCLUDE_CI_FOOTER)]
    message.extend(sorted(tests))
    result.presentation.step_text = '\n * '.join(message)


CI_ONLY = _CiOnly()


class TestSpecBase(object):
  """Abstract base class for specs for tests and wrapped tests."""

  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def get_test(self, chromium_tests_api):
    """Get a test instance described by the spec.

    Returns:
      An instance of either a `Test` subclass or an instance of a
      `TestWrapper` subclass.
    """
    raise NotImplementedError()  # pragma: no cover

  @abc.abstractmethod
  def disable(self, disabled_reason):
    raise NotImplementedError()  # pragma: no cover


@attrs()
class TestSpec(TestSpecBase):
  """Abstract base class for specs for tests.

  Attributes:
    * name - The displayed name of the test.
    * target_name - The ninja build target for the test, a key in
      //testing/buildbot/gn_isolate_map.pyl, e.g. "browser_tests".
    * disabled_reason - A object indicating a reason to disable the test
      (e.g. a ci_only test that won't be run on a try builder). If this
      is not None, then get_test should not be called on the spec.
    * full_test_target - A fully qualified Ninja target, e.g.
      "//chrome/test:browser_tests".
    * waterfall_builder_group - The matching waterfall builder group.
      This value would be the builder group of the mirrored builder for
      a try builder.
    * waterfall_buildername - The matching waterfall builder name. This
      value would be the name of the mirrored builder for a try builder.
    * resultdb - The ResultDB integration configuration. If
      `resultdb.enable` is not True, then ResultDB integration is
      disabled.
    * test_id_prefix: A prefix to be added to the test Id for the test
      e.g.
      "ninja://chrome/test:telemetry_gpu_integration_test/trace_test/".
  """

  _name = attrib(str)
  target_name = attrib(str)
  disabled_reason = attrib(DisabledReason, default=None)
  info_messages = attrib(sequence[str], default=())
  full_test_target = attrib(str, default=None)
  waterfall_builder_group = attrib(str, default=None)
  waterfall_buildername = attrib(str, default=None)
  resultdb = attrib(ResultDB, default=ResultDB.create())
  # TODO(crbug/1106965): remove test_id_prefix, if deriver gets turned down.
  test_id_prefix = attrib(str, default=None)

  @property
  def name(self):
    """The name of the step without a phase suffix.

    Additional suffixes may be present (e.g. os and GPU for swarming
    tests).
    """
    return self._name

  @property
  def canonical_name(self):
    """Canonical name of the test, no suffix attached."""
    return self._name

  @classmethod
  def create(cls, name, **kwargs):
    """Create a TestSpec.

    Arguments:
      * name - The name of the test. The returned spec will have this
        value for name.
      * kwargs - Additional keyword arguments that will be used to
        initialize the attributes of the returned spec. If the
        `target_name` keyword is not set, the `target_name` attribute of
        the returned spec have the value of `name`.
    """
    kwargs['target_name'] = kwargs.get('target_name') or name
    return cls(name=name, **kwargs)

  @abc.abstractproperty
  def test_class(self):
    """The test class associated with the spec."""
    raise NotImplementedError()  # pragma: no cover

  def get_test(self, chromium_tests_api):
    """Get the test described by the spec.

    It is an error to call this method if disabled_reason is not None.
    """
    assert not self.disabled_reason
    return self.test_class(self, chromium_tests_api)

  def disable(self, disabled_reason):
    return attr.evolve(self, disabled_reason=disabled_reason)

  def add_info_message(self, message):
    return attr.evolve(self, info_messages=self.info_messages + (message,))


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

  def __init__(self, spec, chromium_tests_api):
    super(Test, self).__init__()

    self.spec = spec
    self._chromium_tests_api = chromium_tests_api

    self._test_options = TestOptions()

    # Contains a set of flaky failures that are known to be flaky, along with
    # the according id of the monorail bug filed for the flaky test.
    # The set of flaky tests is supposed to be a subset of the deterministic
    # failures.
    self._known_flaky_failures_map = {}

    # A map from suffix [e.g. 'with patch'] to the name of the recipe engine
    # step that was invoked in run(). This makes the assumption that run() only
    # emits a single recipe engine step, and that the recipe engine step is the
    # one that best represents the run of the tests. This is used by FindIt to
    # look up the failing step for a test suite from buildbucket.
    self._suffix_step_name_map = {}

    # Used to track results of tests as reported by RDB. Separate from
    # _deterministic_failures above as that is populated by parsing the tests'
    # JSON results, while this field is populated entirely by RDB's API. Also
    # keyed via suffix like _deterministic_failures above.
    self._rdb_results = {}

    # Maps suffix to wheter or not the test exited non-zero. In conjunction with
    # _rdb_results above, can safely handle any type of test failure without
    # inspecting JSON.
    self._failure_on_exit_suffix_map = {}

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
    return self.spec.name

  @property
  def canonical_name(self):
    """Canonical name of the test, no suffix attached."""
    return self.spec.canonical_name

  @property
  def target_name(self):
    return self.spec.target_name

  @property
  def full_test_target(self):
    """A fully qualified Ninja target, e.g. "//chrome/test:browser_tests"."""
    return self.spec.full_test_target

  @property
  def test_id_prefix(self):
    """Prefix of test_id in ResultDB. e.g.

    "ninja://chrome/test:telemetry_gpu_integration_test/trace_test/"
    """
    return self.spec.test_id_prefix

  @property
  def resultdb(self):
    """Configuration of ResultDB integration in the test.

    Returns a ResultDB instance.
    """
    return self.spec.resultdb

  @property
  def isolate_target(self):
    """Returns isolate target name. Defaults to None."""
    return None

  @property
  def uses_isolate(self):
    """Returns true if the test is run via an isolate.

    This does not need to be overridden in any subclasses. Overriding
    isolate_target to return a non-false value will cause the test to
    report that it uses isolate.
    """
    return bool(self.isolate_target)

  @property
  def is_skylabtest(self):
    return False

  @property
  def runs_on_swarming(self):
    return False

  @property
  def api(self):
    """Returns the chromium_tests RecipeApi object associated with the test."""
    return self._chromium_tests_api

  def prep_local_rdb(self, temp=None, include_artifacts=True):
    """Returns a ResultDB instance suitable for local test runs.

    Main difference between remote swarming runs and local test runs (ie:
    ScriptTests and LocalIsolatedScriptTests) is the location of a temp
    result file and the location of the result_adapter binary.

    Args:
      api: Recipe API object.
      temp: Path to temp file to store results.
      include_artifacts: If True, add the parent dir of temp as an artifact dir.
    """
    temp = temp or self.api.m.path.mkstemp()
    artifact_dir = self.api.m.path.dirname(temp) if include_artifacts else ''
    base_tags = None
    if (self.api.m.chromium.c and self.api.m.chromium.c.TARGET_PLATFORM):
      base_tags = (('target_platform', self.api.m.chromium.c.TARGET_PLATFORM),)
    resultdb = attr.evolve(
        self.spec.resultdb,
        artifact_directory=artifact_dir,
        base_tags=base_tags,
        base_variant=dict(
            self.spec.resultdb.base_variant or {},
            test_suite=self.canonical_name),
        result_adapter_path=str(self.api.m.path['checkout'].join(
            'tools', 'resultdb', 'result_adapter')),
        result_file=self.api.m.path.abspath(temp),
        # Give each local test suite its own invocation to make it easier to
        # fetch results.
        include=True)
    return resultdb

  @abc.abstractmethod
  def get_invocation_names(self, _suffix):
    """Returns the invocation names tracking the test's results in RDB."""
    raise NotImplementedError()  # pragma: no cover

  def get_rdb_results(self, suffix):
    return self._rdb_results.get(suffix)

  def update_rdb_results(self, suffix, results):
    self._rdb_results[suffix] = results

  @property
  def known_flaky_failures(self):
    """Return a set of tests that failed but known to be flaky at ToT."""
    return set(self._known_flaky_failures_map)

  def get_summary_of_known_flaky_failures(self):
    """Returns a set of text to use to display in the test results summary."""
    return {
        '%s: crbug.com/%s' % (test_name, issue_id)
        for test_name, issue_id in six.iteritems(self._known_flaky_failures_map)
    }

  def add_known_flaky_failure(self, test_name, monorail_issue):
    """Add a known flaky failure on ToT along with the monorail issue id."""
    self._known_flaky_failures_map[test_name] = monorail_issue

  def compile_targets(self):
    """List of compile targets needed by this test."""
    raise NotImplementedError()  # pragma: no cover

  def pre_run(self, suffix):  # pragma: no cover
    """Steps to execute before running the test."""
    del suffix
    return []

  @recipe_api.composite_step
  def run(self, suffix):  # pragma: no cover
    """Run the test.

    Implementations of this method must populate
    self._suffix_step_name_map[suffix] with the name of the recipe engine step
    that best represents the work performed by this Test.

    suffix is 'with patch' or 'without patch'

    Returns:
      step.StepData for the step representing the test that ran, or None if
        there was an error when preparing the test.
    """
    raise NotImplementedError()

  def update_failure_on_exit(self, suffix, failure_on_exit):
    self._failure_on_exit_suffix_map[suffix] = failure_on_exit
    rdb_results = self._rdb_results.get(suffix)
    if rdb_results:
      self._rdb_results[suffix] = rdb_results.with_failure_on_exit(
          failure_on_exit)

  def failure_on_exit(self, suffix):
    """Returns True if the test (or any of its shards) exited non-zero.

    Used to determine the result of the test in the absence of anything
    uploaded to RDB. For safety, assume any test that fails to update
    _failure_on_exit_suffix_map resulted in a failure.
    """
    return self._failure_on_exit_suffix_map.get(suffix, True)

  def has_valid_results(self, suffix):
    """
    Returns True if results (failures) are valid.

    This makes it possible to distinguish between the case of no failures
    and the test failing to even report its results in machine-readable
    format.
    """
    if suffix not in self._rdb_results:
      return False

    return not self._rdb_results[suffix].invalid

  def pass_fail_counts(self, suffix):
    """Returns a dictionary of pass and fail counts for each test.

    Format looks like:
    {
      'test1': {
        'pass_count': int,
        'fail_count': int,
      },
      ...
    }
    """
    results = self.get_rdb_results(suffix)
    pass_fail_counts = {}
    for t, runs in six.iteritems(results.individual_results):
      pass_fail_counts[t] = {
          'pass_count': len([r for r in runs if r == test_result_pb2.PASS]),
          'fail_count': len([r for r in runs if r != test_result_pb2.PASS]),
      }
    return pass_fail_counts

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
    with_patch_total = self._rdb_results['with patch'].total_tests_ran
    with_patch_retry_total = (
        self._rdb_results['retry shards with patch'].total_tests_ran
        if 'retry shards with patch' in self._rdb_results else 0)
    total_tests_ran = max(with_patch_total, with_patch_retry_total)
    assert total_tests_ran, (
        "We cannot compute the total number of tests to re-run if no tests "
        "were run 'with patch'. Expected the results tracker to contain key "
        "'total_tests_ran', but it didn't")

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
    return int(
        min(
            min(
                max(
                    original_num_shards * REPEAT_COUNT_FOR_FAILING_TESTS *
                    (float(num_tests_to_retry) / total_tests_ran), 1),
                original_num_shards), num_tests_to_retry))

  def failures(self, suffix):
    """Return tests that failed at least once (list of strings)."""
    failure_msg = (
        'There is no data for the test run suffix ({0}). This should never '
        'happen as all calls to failures() should first check that the data '
        'exists.'.format(suffix))
    assert suffix in self._rdb_results, failure_msg
    return self._rdb_results[suffix].unexpected_failing_tests

  def deterministic_failures(self, suffix):
    """Return tests that failed on every test run(list of strings)."""
    failure_msg = (
        'There is no data for the test run suffix ({0}). This should never '
        'happen as all calls to deterministic_failures() should first check '
        'that the data exists.'.format(suffix))
    assert suffix in self._rdb_results, failure_msg
    return self._rdb_results[suffix].unexpected_failing_tests

  def notrun_failures(self, suffix):
    """Returns tests that had status NOTRUN/UNKNOWN.

    FindIt has special logic for handling for tests with status NOTRUN/UNKNOWN.
    This method returns test for which every test run had a result of either
    NOTRUN or UNKNOWN.

    Returns:
      not_run_tests: A set of strings. Only valid if valid_results is True.
    """
    assert self.has_valid_results(suffix), (
        'notrun_failures must only be called when the test run is known to '
        'have valid results.')
    return self._rdb_results[suffix].unexpected_skipped_tests

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
  def uses_local_devices(self):
    return False  # pragma: no cover

  def step_name(self, suffix):
    """Helper to uniformly combine tests's name with a suffix.

    Note this step_name is not necessarily the same as the step_name in actual
    builds, since there could be post-processing on the step_name by other
    apis, like swarming (see api.chromium_swarming.get_step_name()).
    """
    return _add_suffix(self.name, suffix)

  def step_metadata(self, suffix=None):
    data = {
        'waterfall_builder_group': self.spec.waterfall_builder_group,
        'waterfall_buildername': self.spec.waterfall_buildername,
        'canonical_step_name': self.canonical_name,
        'isolate_target_name': self.isolate_target,
    }
    if suffix is not None:
      data['patched'] = suffix in ('with patch', 'retry shards with patch')
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
      retry_shards_failures = self.deterministic_failures(retry_suffix)

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
    for test_name, results in six.iteritems(pass_fail_counts):
      # If a test fails at least once, then it's flaky on tip of tree and we
      # should ignore it.
      if results['fail_count'] > 0:
        ignored_failures.add(test_name)
    return (True, ignored_failures)

  def shard_retry_with_patch_results(self):
    """Returns passing and failing tests ran for 'retry shards with patch'.

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

    initial_failing_tests = set()
    for test_name, result in six.iteritems(self.pass_fail_counts('with patch')):
      if result['fail_count'] > 0:
        initial_failing_tests.add(test_name)

    passing_tests = set()
    failing_tests = set()
    for test_name, result in six.iteritems(self.pass_fail_counts(suffix)):
      if result['fail_count'] > 0:
        failing_tests.add(test_name)

    # If a test failed in 'with patch' but didn't fail in 'retry shards with
    # patch', assume it passed. This is needed when fetching results from RDB
    # since we only fetch tests with unexpected results.
    for t in initial_failing_tests:
      if not self.pass_fail_counts(suffix).get(t, {}):
        passing_tests.add(t)

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

  def present_rdb_results(self, step_result, rdb_results):
    """Add a summary of test failures tracked in RDB to the given step_result.

    This duplicates info present in the "Test Results" tab in the new Milo UI.
    TODO(crbug.com/1245085): Remove this if/when all users have migrated to
    the new UI.
    """
    if not rdb_results or not rdb_results.unexpected_failing_tests:
      return

    failures, failures_text = self.api.m.test_utils.limit_failures(
        sorted(rdb_results.unexpected_failing_tests))
    step_result.presentation.step_text += (
        self.api.m.presentation_utils.format_step_text(
            [['deterministic failures [caused step to fail]:', failures_text]]))
    for failure in failures:
      results_url = self.api.get_milo_test_results_url(failure)
      step_result.presentation.links[failure] = results_url


@attrs()
class TestWrapperSpec(TestSpecBase):
  """Abstract base class for specs for test wrappers.

  Attributes:
    * test_spec - The spec for the wrapped test.
  """

  test_spec = attrib(TestSpecBase)

  @classmethod
  def create(cls, test_spec, **kwargs):
    """Create a TestWrapperSpec.

    Arguments:
      * test_spec - The spec for the wrapped test.
      * kwargs - Additional keyword arguments that will be used to
        initialize the attributes of the returned spec.
    """
    return cls(test_spec, **kwargs)

  def get_test(self, chromium_tests_api):
    """Get the test described by the spec."""
    return self.test_wrapper_class(self,
                                   self.test_spec.get_test(chromium_tests_api))

  @property
  def disabled_reason(self):
    return self.test_spec.disabled_reason

  @abc.abstractproperty
  def test_wrapper_class(self):
    """The test wrapper class associated with the spec."""
    raise NotImplementedError()  # pragma: no cover

  @property
  def name(self):
    """The name of the test."""
    return self.test_spec.name

  def disable(self, disabled_reason):
    return attr.evolve(self, test_spec=self.test_spec.disable(disabled_reason))

  def add_info_message(self, m):
    return attr.evolve(self, test_spec=self.test_spec.add_info_message(m))


class TestWrapper(Test):  # pragma: no cover
  """ A base class for Tests that wrap other Tests.

  By default, all functionality defers to the wrapped Test.
  """

  def __init__(self, spec, test):
    super(TestWrapper, self).__init__(test.name, test.api)
    self.spec = spec
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
  def full_test_target(self):
    return self._test.full_test_target

  @property
  def test_id_prefix(self):
    return self._test.test_id_prefix

  @property
  def result_db(self):
    return self._test.result_db

  @property
  def canonical_name(self):
    return self._test.canonical_name

  @property
  def isolate_target(self):
    return self._test.isolate_target

  def compile_targets(self):
    return self._test.compile_targets()

  def name_of_step_for_suffix(self, suffix):
    return self._test.name_of_step_for_suffix(suffix)

  def pre_run(self, suffix):
    return self._test.pre_run(suffix)

  @recipe_api.composite_step
  def run(self, suffix):
    return self._test.run(suffix)

  def has_valid_results(self, suffix):
    return self._test.has_valid_results(suffix)

  def failures(self, suffix):
    return self._test.failures(suffix)

  def deterministic_failures(self, suffix):
    return self._test.deterministic_failures(suffix)

  def notrun_failures(self, suffix):
    return self._test.notrun_failures(suffix)

  def pass_fail_counts(self, suffix):
    return self._test.pass_fail_counts(suffix)

  @property
  def uses_local_devices(self):
    return self._test.uses_local_devices

  def step_metadata(self, suffix=None):
    return self._test.step_metadata(suffix=suffix)

  @property
  def target_name(self):
    return self._test.target_name

  @property
  def raw_cmd(self):
    return self._test.raw_cmd

  @raw_cmd.setter
  def raw_cmd(self, value):
    self._test.raw_cmd = value

  @property
  def relative_cwd(self):
    return self._test.relative_cwd

  @raw_cmd.setter
  def relative_cwd(self, value):
    self._test.relative_cwd = value

  @property
  def runs_on_swarming(self):
    return self._test.runs_on_swarming

  @property
  def isolate_coverage_data(self):
    return self._test.isolate_coverage_data

  @property
  def isolate_profile_data(self):
    return self._test.isolate_profile_data

  def get_invocation_names(self, suffix):
    return self._test.get_invocation_names(suffix)

  def get_rdb_results(self, suffix):
    return self._test.get_rdb_results(suffix)

  def update_rdb_results(self, suffix, results):
    return self._test.update_rdb_results(suffix, results)


class _NotInExperiment(DisabledReason):
  """Identifies an experimental test that is not being triggered."""

  def report_tests(self, chromium_tests_api, tests):
    result = chromium_tests_api.m.step('experimental tests not in experiment',
                                       [])
    message = [('The following experimental tests were not selected'
                ' for their experiments in this build:')]
    message.extend(sorted(tests))
    result.presentation.step_text = '\n * '.join(message)


_NOT_IN_EXPERIMENT = _NotInExperiment()


@attrs()
class ExperimentalTestSpec(TestWrapperSpec):
  """A spec for a test to be executed at some percentage."""

  @classmethod
  def create(cls, test_spec, experiment_percentage, api):  # pylint: disable=line-too-long,arguments-differ
    """Create an ExperimentalTestSpec.

    Arguments:
      * test_spec - The spec of the wrapped test.
      * experiment_percentage - The percentage chance that the test will be
        executed.
      * api - An api object providing access to the buildbucket and tryserver
        recipe modules.
    """
    experiment_percentage = max(0, min(100, int(experiment_percentage)))
    is_in_experiment = cls._calculate_is_in_experiment(test_spec,
                                                       experiment_percentage,
                                                       api)
    if not is_in_experiment:
      test_spec = test_spec.disable(_NOT_IN_EXPERIMENT)
    return super(ExperimentalTestSpec, cls).create(test_spec)

  @property
  def test_wrapper_class(self):
    """The test wrapper class associated with the spec."""
    return ExperimentalTest

  @staticmethod
  def _calculate_is_in_experiment(test_spec, experiment_percentage, api):
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
        test_spec.name,
    ]

    digest = hashlib.sha1(''.join(
        str(c) for c in criteria).encode('utf-8')).digest()
    short = struct.unpack_from('<H', digest)[0]
    return experiment_percentage * 0xffff >= short * 100


class ExperimentalTest(TestWrapper):
  """A test wrapper that runs the wrapped test on an experimental test.

  Experimental tests:
    - can run at <= 100%, depending on the experiment_percentage.
    - will not cause the build to fail.
  """

  def _experimental_suffix(self, suffix):
    if not suffix:
      return 'experimental'
    return '%s, experimental' % (suffix)

  def _actually_has_valid_results(self, suffix):
    """Check if the underlying test produced valid results.

    The ExperimentalTest reports that it always has valid results, so
    various result methods (failures, notrun_failures, etc.) will be
    called. If the underlying test does not have valid results, then
    calling the superclass version of the method would violate the
    contract, so this method indicates if calling the superclass version
    should be safe.
    """
    return super(ExperimentalTest,
                 self).has_valid_results(self._experimental_suffix(suffix))

  @property
  def abort_on_failure(self):
    return False

  #override
  def pre_run(self, suffix):
    try:
      return super(ExperimentalTest,
                   self).pre_run(self._experimental_suffix(suffix))
    except self.api.m.step.StepFailure:
      pass

  #override
  def name_of_step_for_suffix(self, suffix):
    experimental_suffix = self._experimental_suffix(suffix)
    return super(ExperimentalTest,
                 self).name_of_step_for_suffix(experimental_suffix)

  #override
  @recipe_api.composite_step
  def run(self, suffix):
    try:
      return super(ExperimentalTest,
                   self).run(self._experimental_suffix(suffix))
    except self.api.m.step.StepFailure:
      pass

  #override
  def has_valid_results(self, suffix):
    # Call the wrapped test's implementation in case it has side effects, but
    # ignore the result.
    super(ExperimentalTest,
          self).has_valid_results(self._experimental_suffix(suffix))
    return True

  #override
  def failures(self, suffix):
    if self._actually_has_valid_results(suffix):
      # Call the wrapped test's implementation in case it has side effects,
      # but ignore the result.
      super(ExperimentalTest, self).failures(self._experimental_suffix(suffix))
    return []

  #override
  def deterministic_failures(self, suffix):
    if self._actually_has_valid_results(suffix):
      # Call the wrapped test's implementation in case it has side effects,
      # but ignore the result.
      super(ExperimentalTest,
            self).deterministic_failures(self._experimental_suffix(suffix))
    return []

  #override
  def notrun_failures(self, suffix):  # pragma: no cover
    if self._actually_has_valid_results(suffix):
      # Call the wrapped test's implementation in case it has side effects,
      # but ignore the result.
      super(ExperimentalTest,
            self).notrun_failures(self._experimental_suffix(suffix))
    return set()

  def pass_fail_counts(self, suffix):
    if self._actually_has_valid_results(suffix):
      # Call the wrapped test's implementation in case it has side effects,
      # but ignore the result.
      super(ExperimentalTest,
            self).pass_fail_counts(self._experimental_suffix(suffix))
    return {}

  def get_invocation_names(self, suffix):
    return super(ExperimentalTest,
                 self).get_invocation_names(self._experimental_suffix(suffix))

  def get_rdb_results(self, suffix):
    return super(ExperimentalTest,
                 self).get_rdb_results(self._experimental_suffix(suffix))

  def update_rdb_results(self, suffix, results):
    return super(ExperimentalTest, self).update_rdb_results(
        self._experimental_suffix(suffix), results)


class LocalTest(Test):
  """Abstract class for local tests.

  This class contains logic related to running tests locally, namely for local
  RDB invocations. All of which is intended to be shared with any subclasses.
  """

  # pylint: disable=abstract-method

  def __init__(self, spec, chromium_tests_api):
    super(LocalTest, self).__init__(spec, chromium_tests_api)
    self._suffix_to_invocation_names = {}

  def get_invocation_names(self, suffix):
    inv = self._suffix_to_invocation_names.get(suffix)
    return [inv] if inv else []

  def update_inv_name_from_stderr(self, stderr, suffix):
    """Scans the given stderr for a local test for the test's invocation name.

    And updates self._suffix_to_invocation_names with the name.

    Args:
      stderr: stderr from the step_data.StepData obj returned from the step
          wrapped with `rdb stream -new ...`.
      suffix: String suffix representing the phase of the build.
    """
    # TODO(crbug.com/1227180): Specify our own custom invocation name rather
    # than parsing stderr.
    match = RDB_INVOCATION_NAME_RE.search(stderr)
    if match:
      inv_name = match.group(1)
      self._suffix_to_invocation_names[suffix] = inv_name


# TODO(gbeaty) Simplify ScriptTestSpec/ScriptTest to just have the compile
# targets for the script rather than having a mapping with all compile targets
# and optional override compile targets
@attrs()
class ScriptTestSpec(TestSpec):
  """A spec for a test that runs a script.

  Attributes:
    * script - The filename of a script to run. The script must be
      located within the //testing/scripts directory of the checkout.
    * all_compile_targets - A mapping of script names to the compile
      targets that need to be built to run the script.
    * script_args - Arguments to be passed to the script.
    * override_compile_targets - The compile targets that need to be
      built to run the script. If a non-empty value is provided, the
      `all_compile_targets` attribute will be ignored.
  """

  script = attrib(str)
  all_compile_targets = attrib(mapping[str, sequence[str]])
  script_args = attrib(command_args, default=())
  override_compile_targets = attrib(sequence[str], default=())

  @property
  def test_class(self):
    """The test class associated with the spec."""
    return ScriptTest


class ScriptTest(LocalTest):  # pylint: disable=W0232
  """
  Test which uses logic from script inside chromium repo.

  This makes it possible to keep the logic src-side as opposed
  to the build repo most Chromium developers are unfamiliar with.

  Another advantage is being to test changes to these scripts
  on trybots.

  All new tests are strongly encouraged to use this infrastructure.
  """

  def __init__(self, spec, chromium_tests_api):
    super(ScriptTest, self).__init__(spec, chromium_tests_api)

  def compile_targets(self):
    if self.spec.override_compile_targets:
      return self.spec.override_compile_targets

    substitutions = {'name': self.spec.name}

    if not self.spec.script in self.spec.all_compile_targets:
      return []

    return [
        string.Template(s).safe_substitute(substitutions)
        for s in self.spec.all_compile_targets[self.spec.script]
    ]

  @recipe_api.composite_step
  def run(self, suffix):
    run_args = []

    tests_to_retry = self._tests_to_retry(suffix)
    if tests_to_retry:
      run_args.extend(['--filter-file',
                       self.api.m.json.input(tests_to_retry)
                      ])  # pragma: no cover

    resultdb = self.prep_local_rdb()

    step_test_data = lambda: (
        self.api.m.json.test_api.output({
            'valid': True,
            'failures': []
        }) + self.api.m.raw_io.test_api.stream_output_text(
            'rdb-stream: included "invocations/test-name" in '
            '"invocations/build-inv"', 'stderr'))

    script_args = []
    if self.spec.script_args:
      script_args = ['--args', self.api.m.json.input(self.spec.script_args)]
    result = self.api.m.build.python(
        self.step_name(suffix),
        # Enforce that all scripts are in the specified directory for
        # consistency.
        self.api.m.path['checkout'].join(
            'testing', 'scripts', self.api.m.path.basename(self.spec.script)),
        args=(self.api.m.chromium_tests.get_common_args_for_scripts() +
              script_args +
              ['run', '--output', self.api.m.json.output()] + run_args),
        raise_on_failure=False,
        resultdb=resultdb if resultdb else None,
        stderr=self.api.m.raw_io.output_text(
            add_output_log=True, name='stderr'),
        venv=True,  # Runs the test through vpython.
        step_test_data=step_test_data)

    status = result.presentation.status

    self._suffix_step_name_map[suffix] = '.'.join(result.name_tokens)

    failures = None
    if result.json.output:
      failures = result.json.output.get('failures')
    if failures is None:
      self.api.m.step.empty(
          '%s with suffix %s had an invalid result' % (self.name, suffix),
          status=self.api.m.step.FAILURE,
          step_text=(
              'The recipe expected the result to contain the key \'failures\'.'
              ' Contents are:\n%s' %
              self.api.m.json.dumps(result.json.output, indent=2)))

    # Most scripts do not emit 'successes'. If they start emitting 'successes',
    # then we can create a proper results dictionary.
    pass_fail_counts = {}
    for failing_test in failures:
      pass_fail_counts.setdefault(failing_test, {
          'pass_count': 0,
          'fail_count': 0
      })
      pass_fail_counts[failing_test]['fail_count'] += 1

    self.update_failure_on_exit(suffix, result.retcode != 0)

    _, failures = self.api.m.test_utils.limit_failures(failures)
    result.presentation.step_text += (
        self.api.m.presentation_utils.format_step_text([['failures:',
                                                         failures]]))

    self.update_inv_name_from_stderr(result.stderr, suffix)

    _present_info_messages(result.presentation, self)

    return self.api.m.step.raise_on_failure(result, status)


@attrs()
class SetUpScript(object):
  """Configuration of a script to run before test execution.

  Attributes:
    * name - The name of the step to execute the script.
    * script - The path to the script.
    * args - The command-line arguments to pass to the script.
  """

  name = attrib(str)
  script = attrib(Path)
  args = attrib(command_args, default=())

  @classmethod
  def create(cls, **kwargs):
    """Create a SetUpScript with attributes initialized with kwargs."""
    return cls(**kwargs)


@attrs()
class TearDownScript(object):
  """Configuration of a script to run after test execution.

  Attributes:
    * name - The name of the step to execute the script.
    * script - The path to the script.
    * args - The command-line arguments to pass to the script.
  """

  name = attrib(str)
  script = attrib(Path)
  args = attrib(command_args, default=())

  @classmethod
  def create(cls, **kwargs):
    """Create a TearDownScript with attributes initialized with kwargs.
    """
    return cls(**kwargs)


@attrs()
class LocalGTestTestSpec(TestSpec):
  """A spec for a test that runs a gtest-based test locally.

  Attributes:
    * args - Arguments to be passed to the test.
    * override_compile_targets - An optional list of compile targets to
      be built to run the test. If not provided the `target_name`
      attribute of the spec will be the only compile target.
    * revision - Revision of the chrome checkout.
    * webkit_revision - Revision of the webkit checkout.
    * android_shard_timeout - For tests on Android, the timeout to be
      applied to the shards.
    * commit_position_property - The name of the property containing
      chromium's commit position.
    * use_xvfb - Whether to use the X virtual frame buffer. Only has an
      effect on Linux. Mostly harmless to set this, except on GPU
      builders.
    * set_up - Scripts to run before running the test.
    * tear_down - Scripts to run after running the test.
    * annotate - Specify which type of test to parse.
    * perf_config - Source side configuration for perf test.
    * perf_builder_name_alias - Previously perf-id, another ID to use
                                when uploading perf results.
  """

  args = attrib(command_args, default=())
  override_compile_targets = attrib(sequence[str], default=())
  revision = attrib(str, default=None)
  webkit_revision = attrib(str, default=None)
  android_shard_timeout = attrib(int, default=None)
  commit_position_property = attrib(str, default='got_revision_cp')
  use_xvfb = attrib(bool, default=True)
  set_up = attrib(sequence[SetUpScript], default=())
  tear_down = attrib(sequence[TearDownScript], default=())
  annotate = attrib(str, default='gtest')
  perf_config = attrib(mapping[str, ...], default={})
  perf_builder_name_alias = attrib(str, default=None)

  @property
  def test_class(self):
    """The test class associated with the spec."""
    return LocalGTestTest


class LocalGTestTest(LocalTest):

  def __init__(self, spec, chromium_tests_api):
    super(LocalGTestTest, self).__init__(spec, chromium_tests_api)
    self._gtest_results = {}

  @Test.test_options.setter
  def test_options(self, value):
    self._test_options = value

  @property
  def set_up(self):
    return self.spec.set_up

  @property
  def tear_down(self):
    return self.spec.tear_down

  @property
  def uses_local_devices(self):
    return True  # pragma: no cover

  def compile_targets(self):
    return self.spec.override_compile_targets or [self.spec.target_name]

  def _get_revision(self, conf):
    substitutions = {
        'webrtc_got_rev':
            self.api.m.bot_update.last_returned_properties.get(
                'got_webrtc_revision')
    }
    return {
        k: string.Template(v).safe_substitute(substitutions)
        for k, v in conf.items()
    }

  @recipe_api.composite_step
  def run(self, suffix):
    tests_to_retry = self._tests_to_retry(suffix)
    test_options = _test_options_for_running(self.test_options, suffix,
                                             tests_to_retry)
    args = _merge_args_and_test_options(self, self.spec.args, test_options)

    if tests_to_retry:
      args = _merge_arg(args, '--gtest_filter', ':'.join(tests_to_retry))

    resultdb = self.prep_local_rdb(include_artifacts=False)
    gtest_results_file = self.api.m.json.output(
        add_json_log=False, leak_to=resultdb.result_file)

    step_test_data = lambda: (
        self.api.m.test_utils.test_api.canned_gtest_output(True) + self.api.m.
        raw_io.test_api.stream_output_text(
            'rdb-stream: included "invocations/some-inv-name" in '
            '"invocations/parent-inv-name"', 'stderr'))

    kwargs = {
        'name': self.step_name(suffix),
        'args': args,
        'step_test_data': step_test_data,
        'resultdb': resultdb,
    }
    kwargs['xvfb'] = self.spec.use_xvfb
    kwargs['test_type'] = self.name
    kwargs['annotate'] = self.spec.annotate
    kwargs['test_launcher_summary_output'] = gtest_results_file

    if self.spec.perf_config:
      kwargs['perf_config'] = self._get_revision(self.spec.perf_config)
      kwargs['results_url'] = RESULTS_URL
      kwargs['perf_dashboard_id'] = self.spec.name
      kwargs['perf_builder_name_alias'] = self.spec.perf_builder_name_alias

    step_result = self.api.m.chromium.runtest(
        self.target_name,
        revision=self.spec.revision,
        webkit_revision=self.spec.webkit_revision,
        stderr=self.api.m.raw_io.output_text(
            add_output_log=True, name='stderr'),
        raise_on_failure=False,
        **kwargs)

    status = step_result.presentation.status

    # TODO(kbr): add functionality to generate_gtest to be able to force running
    # these local gtests via isolate from the src-side JSON files.
    # crbug.com/584469
    self._suffix_step_name_map[suffix] = '.'.join(step_result.name_tokens)
    self.update_failure_on_exit(suffix, step_result.retcode != 0)

    self.update_inv_name_from_stderr(step_result.stderr, suffix)

    _present_info_messages(step_result.presentation, self)

    results_to_upload = gtest_results_file
    if results_to_upload:
      self.api.m.test_results.upload(
          results_to_upload,
          test_type=self.name,
          chrome_revision=self.api.m.bot_update.last_returned_properties.get(
              self.spec.commit_position_property, 'refs/x@{#0}'))

    return self.api.m.step.raise_on_failure(step_result, status)


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

  return _add_suffix(step_name, suffix)


def _archive_layout_test_results(api, step_name, step_suffix=None):
  # LayoutTest's special archive and upload results
  results_dir = api.path['start_dir'].join('layout-test-results')

  buildername = api.buildbucket.builder_name
  buildnumber = api.buildbucket.build.number

  archive_layout_test_results = api.chromium.repo_resource(
      'recipes', 'chromium', 'archive_layout_test_results.py')

  archive_layout_test_args = [
      '--results-dir',
      results_dir,
      '--build-dir',
      api.chromium.c.build_dir,
      '--build-number',
      buildnumber,
      '--builder-name',
      buildername,
      '--gs-bucket',
      'gs://chromium-layout-test-archives',
      '--staging-dir',
      api.path['cache'].join('chrome_staging'),
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
  archive_result = api.build.python(archive_step_name,
                                    archive_layout_test_results,
                                    archive_layout_test_args)

  # TODO(tansell): Move this to render_results function
  sanitized_buildername = re.sub('[ .()]', '_', buildername)
  base = ("https://test-results.appspot.com/data/layout_results/%s/%s" %
          (sanitized_buildername, buildnumber))
  base += '/' + urllib.parse.quote(step_name)

  archive_result.presentation.links['layout_test_results'] = (
      base + '/layout-test-results/results.html')
  archive_result.presentation.links['(zip)'] = (
      base + '/layout-test-results.zip')
  return base + '/layout-test-results/results.html'


@attrs()
class SwarmingTestSpec(TestSpec):
  """Spec for a test that runs via swarming.

  Attributes:
    * cipd_packages - The CIPD packages to be loaded for the test's
      swarming tasks.
    * containment_type - The type of containment to use for the test's
      swarming tasks. See `swarming.py trigger --help` for more info.
    * dimensions - Requested dimensions of the test. The keys are
      dimension names. The values are the value of the dimensions or
      None to clear a dimension.
    * expiration - The expiration timeout in seconds of the test's
      swarming tasks.
    * optional_dimensions - Optional dimensions that create additional
      fallback task sices. The keys are cumulative expiration times for
      the additional slices mapping to dicts of the same form as the
      `dimensions` attribute. Additional task slices will be created for
      each item, in order of the expiration time for the item using the
      dimensions specified in the value. The final slice will set the
      dimensions according to the `dimensions` attribute.
    * extra_suffix - An additional suffix applied to the test's step
      name.
    * hard_timeout - The execution timeout in seconds of the test's
      swarming tasks.
    * io_timeout - The maximum amount of time in seconds swarming will
      allow the task to be silent (no stdout or stderr).
    * trigger_script - An optional script used for triggering the test's
      swarming tasks.
    * set_up - Scripts to run before running the test.
    * tear_down - Scripts to run after running the test.
    * merge - An optional script used for merging results between the
      test's swarming tasks.
    * args - Arguments to be passed to the test.
    * isolate_coverage_data - Whether to isolate coverage profile data
      during task execution.
    * isolate_profile_data - Whether to isolate profile data during task
      execution.
    * ignore_task_failure - Whether to ignore swarming task failures. If
      False, the test will be reported as StepFailure on failure.
    * named_caches - Named caches to mount for the test's swarming
      tasks. The keys are the named of the cache and the values are the
      path relative to the swarming task's root directory where the
      cache should be mounted.
    * shards - The number of shards to trigger.
    * service_account - The service account to run the test's swarming
      tasks as.
    * idempotent - Whether to mark the test's swarming tasks as
      idempotent. If not provided, the default logic used by the
      `chromium_swarming` recipe module will be used.
  """
  # pylint: disable=abstract-method

  cipd_packages = attrib(sequence[chromium_swarming.CipdPackage], default=())
  containment_type = attrib(str, default=None)
  dimensions = attrib(mapping[str, ...], default={})
  expiration = attrib(int, default=None)
  optional_dimensions = attrib(mapping[int, mapping[str, ...]], default={})
  extra_suffix = attrib(str, default=None)
  hard_timeout = attrib(int, default=None)
  io_timeout = attrib(int, default=None)
  trigger_script = attrib(chromium_swarming.TriggerScript, default=None)
  set_up = attrib(sequence[SetUpScript], default=())
  tear_down = attrib(sequence[TearDownScript], default=())
  merge = attrib(chromium_swarming.MergeScript, default=None)
  args = attrib(command_args, default=())
  isolate_coverage_data = attrib(bool, False)
  isolate_profile_data = attrib(bool, False)
  ignore_task_failure = attrib(bool, False)
  named_caches = attrib(mapping[str, str], default={})
  shards = attrib(int, default=1)
  quickrun_shards = attrib(int, default=None)
  service_account = attrib(str, default=None)
  idempotent = attrib(bool, default=None)

  @classmethod
  def create(cls, name, **kwargs):
    """Create a SwarmingTestSpec.

    Arguments:
      * name - The name of the test.
      * kwargs - Additional keyword arguments that will be used to
        initialize the attributes of the returned spec. If the keyword
        `extra_suffix` is not set, a value will be computed if the
        `'gpu'` dimension is specified or if the `'os'` dimension is
        `'Android'` and the `'device_type'` dimension is set.
    """
    dimensions = kwargs.get('dimensions', {})
    extra_suffix = kwargs.pop('extra_suffix', None)
    if extra_suffix is None:
      if dimensions.get('gpu'):
        extra_suffix = cls._get_gpu_suffix(dimensions)
      elif dimensions.get('os') == 'Android' and dimensions.get('device_type'):
        extra_suffix = cls._get_android_suffix(dimensions)
    return super(SwarmingTestSpec, cls).create(
        name, extra_suffix=extra_suffix, **kwargs)

  @property
  def name(self):
    if self.extra_suffix:
      return '%s %s' % (self._name, self.extra_suffix)
    else:
      return self._name

  def with_shards(self, shards):
    return attr.evolve(self, shards=int(shards))

  @staticmethod
  def _get_gpu_suffix(dimensions):
    gpu_vendor_id = dimensions.get('gpu', '').split(':')[0].lower()
    vendor_ids = {
        '8086': 'Intel',
        '10de': 'NVIDIA',
        '1002': 'AMD',
        'none': 'SwiftShader',  # explicit 'none' means requesting SwS
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
        'flame': 'Pixel 4',
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
        'sunfish': 'Pixel 4a',
        'taimen': 'Pixel 2 XL',
        'walleye': 'Pixel 2',
        'zerofltetmo': 'Galaxy S6',
    }
    targetted_device = dimensions['device_type']
    product_name = device_codenames.get(targetted_device, targetted_device)
    return 'on Android device %s' % product_name


class SwarmingTest(Test):
  # Some suffixes should have marginally higher priority. See crbug.com/937151.
  SUFFIXES_TO_INCREASE_PRIORITY = ['without patch', 'retry shards with patch']

  def __init__(self, spec, chromium_tests_api):
    super(SwarmingTest, self).__init__(spec, chromium_tests_api)

    self._tasks = {}
    self._raw_cmd = []
    self._relative_cwd = None

  def _dispatches_to_windows(self):
    if self.spec.dimensions:
      os = self.spec.dimensions.get('os', '')
      return os.startswith('Windows')
    return False

  @property
  def set_up(self):
    return self.spec.set_up

  @property
  def tear_down(self):
    return self.spec.tear_down

  @property
  def runs_on_swarming(self):
    return True

  @property
  def isolate_target(self):
    return self.target_name

  @property
  def isolate_coverage_data(self):
    return bool(self.spec.isolate_coverage_data)

  @property
  def isolate_profile_data(self):
    # TODO(crbug.com/1075823) - delete isolate_coverage_data once deprecated.
    # Release branches will still be setting isolate_coverage_data under
    # src/testing. Deprecation expected after M83.
    return self.spec.isolate_profile_data or self.isolate_coverage_data

  @property
  def shards(self):
    return self.spec.shards

  @property
  def raw_cmd(self):
    return self._raw_cmd

  @raw_cmd.setter
  def raw_cmd(self, value):
    self._raw_cmd = value

  @property
  def relative_cwd(self):
    return self._relative_cwd

  @relative_cwd.setter
  def relative_cwd(self, value):
    self._relative_cwd = value

  def create_task(self, suffix, task_input):
    """Creates a swarming task. Must be overridden in subclasses.

    Args:
      api: Caller's API.
      suffix: Suffix added to the test name.
      task_input: Hash or digest of the isolated test to be run.

    Returns:
      A SwarmingTask object.
    """
    raise NotImplementedError()  # pragma: no cover

  def _apply_swarming_task_config(self, task, suffix, filter_flag,
                                  filter_delimiter):
    """Applies shared configuration for swarming tasks.
    """
    tests_to_retry = self._tests_to_retry(suffix)
    test_options = _test_options_for_running(self.test_options, suffix,
                                             tests_to_retry)
    args = _merge_args_and_test_options(self, self.spec.args, test_options)

    # If we're in quick run set the shard count to any available quickrun shards
    use_quickrun = (
        self.api.m.cq.active and
        (self.api.m.cq.run_mode == self.api.m.cq.QUICK_DRY_RUN))
    shards = self.spec.quickrun_shards if (
        use_quickrun and self.spec.quickrun_shards) else self.spec.shards

    if tests_to_retry:
      # The filter list is eventually passed to the binary over the command
      # line.  On Windows, the command line max char limit is 8191 characters.
      # On other OSes, the max char limit is over 100,000 characters. We avoid
      # sending the filter list if we're close to the limit -- this causes all
      # tests to be run.
      char_limit = 6000 if self._dispatches_to_windows() else 90000
      expected_filter_length = (
          sum(len(x) for x in tests_to_retry) +
          len(tests_to_retry) * len(filter_delimiter))

      if expected_filter_length < char_limit:
        test_list = filter_delimiter.join(tests_to_retry)
        args = _merge_arg(args, filter_flag, test_list)
        shards = self.shards_to_retry_with(shards, len(tests_to_retry))

    task.extra_args.extend(args)
    task.shards = shards

    task_request = task.request
    task_slice = task_request[0]

    merge = self.spec.merge
    using_pgo = self.api.m.chromium_tests.m.pgo.using_pgo
    if self.isolate_profile_data or using_pgo:
      # Targets built with 'use_clang_coverage' or 'use_clang_profiling' (also
      # set by chrome_pgo_phase=1) will look at this environment variable to
      # determine where to write the profile dumps. The %Nm syntax is understood
      # by this instrumentation, see:
      #   https://clang.llvm.org/docs/SourceBasedCodeCoverage.html#id4
      env_vars = {
          'LLVM_PROFILE_FILE': '${ISOLATED_OUTDIR}/profraw/default-%2m.profraw',
      }

      # crbug.com/1124774 - For PGO, we're increasing the shutdown timeout to
      # 300 seconds to allow sufficient time for all processes to finish writing
      # profiles.
      if using_pgo:
        env_vars['CHROME_SHUTDOWN_TIMEOUT'] = '300'
        if self.api.m.chromium.c.TARGET_PLATFORM == 'android':
          env_vars['CHROME_PGO_PROFILING'] = '1'

      task_slice = task_slice.with_env_vars(**env_vars)

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
      merge = self.api.m.code_coverage.shard_merge(
          self.step_name(suffix),
          self.target_name,
          skip_validation=skip_validation,
          sparse=sparse,
          additional_merge=self.spec.merge or task.merge)

    if suffix.startswith('retry shards'):
      task_slice = task_slice.with_idempotent(False)
    elif self.spec.idempotent is not None:
      task_slice = task_slice.with_idempotent(self.spec.idempotent)

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
      if len(task.shard_indices) == 0:  # pragma: no cover
        self.api.m.step.empty(
            'missing failed shards',
            status=self.api.m.step.FAILURE,
            step_text=(
                "Retry shards with patch is being run on {},"
                " which has no failed shards."
                " This usually happens because of a test runner bug."
                " The test runner reports test failures, but had exit_code 0."
                .format(self.step_name(suffix='with patch'))))
    else:
      task.shard_indices = range(task.shards)

    task.build_properties = self.api.m.chromium.build_properties
    task.containment_type = self.spec.containment_type
    task.ignore_task_failure = self.spec.ignore_task_failure
    if merge:
      task.merge = merge

    task.trigger_script = self.spec.trigger_script

    ensure_file = task_slice.cipd_ensure_file
    for package in self.spec.cipd_packages:
      ensure_file.add_package(package.name, package.version, package.root)

    task_slice = (task_slice.with_cipd_ensure_file(ensure_file))

    task.named_caches.update(self.spec.named_caches)

    if suffix in self.SUFFIXES_TO_INCREASE_PRIORITY:
      task_request = task_request.with_priority(task_request.priority - 1)

    if self.spec.expiration:
      task_slice = task_slice.with_expiration_secs(self.spec.expiration)

    if self.spec.hard_timeout:
      task_slice = task_slice.with_execution_timeout_secs(
          self.spec.hard_timeout)

    if self.spec.io_timeout:
      task_slice = task_slice.with_io_timeout_secs(self.spec.io_timeout)

    task_dimensions = task_slice.dimensions
    # Add custom dimensions.
    task_dimensions.update(self.spec.dimensions)
    # Set default value.
    if 'os' not in task_dimensions:
      task_dimensions['os'] = (
          self.api.m.chromium_swarming.prefered_os_dimension(
              self.api.m.platform.name))
    task_slice = task_slice.with_dimensions(**task_dimensions)

    # Add optional dimensions.
    task.optional_dimensions = self.spec.optional_dimensions

    # Add tags.
    tags = {
        'ninja_target': [self.full_test_target or ''],
        # TODO(crbug/1106965): remove test_id_prefix from tags, if deriver
        # gets turned down.
        'test_id_prefix': [self.test_id_prefix or ''],
        'test_suite': [self.canonical_name],
    }

    task.request = (
        task_request.with_slice(0, task_slice).with_name(
            self.step_name(suffix)).with_service_account(
                self.spec.service_account or '').with_tags(tags))
    return task

  def get_task(self, suffix):
    return self._tasks.get(suffix)

  def get_invocation_names(self, suffix):
    task = self.get_task(suffix)
    if task:
      return task.get_invocation_names()
    return []

  def pre_run(self, suffix):
    """Launches the test on Swarming."""
    assert suffix not in self._tasks, ('Test %s was already triggered' %
                                       self.step_name(suffix))

    task_input = self.api.m.isolate.isolated_tests.get(self.isolate_target)
    if not task_input:
      return self.api.m.step.empty(
          '[error] %s' % self.step_name(suffix),
          status=self.api.m.step.INFRA_FAILURE,
          step_text=('*.isolated file for target %s is missing' %
                     self.isolate_target))

    # Create task.
    self._tasks[suffix] = self.create_task(suffix, task_input)

    # Export TARGET_PLATFORM to resultdb tags
    resultdb = self.resultdb
    if (self.api.m.chromium.c and self.api.m.chromium.c.TARGET_PLATFORM):
      resultdb = attr.evolve(
          resultdb,
          base_tags=(('target_platform',
                      self.api.m.chromium.c.TARGET_PLATFORM),))

    self.api.m.chromium_swarming.trigger_task(
        self._tasks[suffix], resultdb=resultdb)

  def validate_task_results(self, step_result):
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
  def run(self, suffix):
    """Waits for launched test to finish and collects the results."""
    step_result, has_valid_results = (
        self.api.m.chromium_swarming.collect_task(self._tasks[suffix]))
    self._suffix_step_name_map[suffix] = '.'.join(step_result.name_tokens)

    metadata = self.step_metadata(suffix)
    step_result.presentation.logs['step_metadata'] = (self.api.m.json.dumps(
        metadata, indent=2, sort_keys=True)).splitlines()

    # TODO(martiniss): Consider moving this into some sort of base
    # validate_task_results implementation.
    results = self.validate_task_results(step_result)
    if not has_valid_results:
      results['valid'] = False

    self.update_failure_on_exit(suffix, bool(self._tasks[suffix].failed_shards))

    _present_info_messages(step_result.presentation, self)

    self.present_rdb_results(step_result, self._rdb_results.get(suffix))

    return step_result

  def step_metadata(self, suffix=None):
    data = super(SwarmingTest, self).step_metadata(suffix)
    if suffix is not None:
      data['full_step_name'] = self._suffix_step_name_map[suffix]
      data['patched'] = suffix in ('with patch', 'retry shards with patch')
      data['dimensions'] = self._tasks[suffix].request[0].dimensions
      data['swarm_task_ids'] = self._tasks[suffix].get_task_ids()
    return data

@attrs()
class SwarmingGTestTestSpec(SwarmingTestSpec):
  """A spec for a test that runs a gtest-based test via swarming.

  Attributes:
    * override_compile_targets - The compile targets that need to be
      built to run the script. If not provided, the target identified by
      the `target_name` attribute will be used.
  """

  override_compile_targets = attrib(sequence[str], default=())

  @property
  def test_class(self):
    """The test class associated with the spec."""
    return SwarmingGTestTest


class SwarmingGTestTest(SwarmingTest):

  def __init__(self, spec, chromium_tests_api):
    super(SwarmingGTestTest, self).__init__(spec, chromium_tests_api)
    self._gtest_results = {}

  @Test.test_options.setter
  def test_options(self, value):
    self._test_options = value

  def compile_targets(self):
    return self.spec.override_compile_targets or [self.spec.target_name]

  def create_task(self, suffix, cas_input_root):
    json_override = None
    # TODO(crbug.com/1255217): Remove this android exception when logcats and
    # tombstones are in resultdb.
    if self.api.m.chromium.c.TARGET_PLATFORM != 'android':
      json_override = self.api.m.path.mkstemp()
    task = self.api.m.chromium_swarming.gtest_task(
        raw_cmd=self._raw_cmd,
        relative_cwd=self.relative_cwd,
        cas_input_root=cas_input_root,
        failure_as_exception=False,
        collect_json_output_override=json_override)
    self._apply_swarming_task_config(task, suffix, '--gtest_filter', ':')
    return task

  def validate_task_results(self, step_result):
    return {}

  def pass_fail_counts(self, suffix):
    return super(SwarmingGTestTest, self).pass_fail_counts(suffix)

  @recipe_api.composite_step
  def run(self, suffix):
    """Waits for launched test to finish and collects the results."""
    step_result = super(SwarmingGTestTest, self).run(suffix)
    step_name = '.'.join(step_result.name_tokens)
    self._suffix_step_name_map[suffix] = step_name

    # TODO(crbug.com/1255217): Remove this android exception when logcats and
    # tombstones are in resultdb.
    if self.api.m.chromium.c.TARGET_PLATFORM == 'android':
      raw_json_data = self.api.m.json.input(step_result.json.output)
    else:
      raw_json_data = self._tasks[suffix].collect_json_output_override

    if raw_json_data:
      chrome_revision_cp = (
          self.api.m.bot_update.last_returned_properties.get(
              'got_revision_cp', 'refs/x@{#0}'))
      _, chrome_revision = self.api.m.commit_position.parse(chrome_revision_cp)
      chrome_revision = str(chrome_revision)
      self.api.m.test_results.upload(
          raw_json_data, chrome_revision=chrome_revision, test_type=step_name)

    return step_result


@attrs()
class LocalIsolatedScriptTestSpec(TestSpec):
  """Spec for a test that runs an isolated script locally.

  Attributes:
    * args - Arguments to be passed to the test.
    * override_compile_targets - An optional list of compile targets to
      be built to run the test. If not provided the `target_name`
      attribute of the spec will be the only compile target.
    * set_up - Scripts to run before running the test.
    * tear_down - Scripts to run after running the test.
    * results_handler_name - A name identifying the type of
      `ResultsHandler` that will be used for processing the test
      results:
      * 'default' - JSONResultsHandler
      * 'layout tests' - LayoutTestResultsHandler
      * 'fake' - FakeCustomResultsHandler
    * isolate_coverage_data - Whether to isolate coverage profile data
      during task execution.
    * isolate_profile_data - Whether to isolate profile data during task
      execution.
  """

  args = attrib(command_args, default=())
  override_compile_targets = attrib(sequence[str], default=())
  set_up = attrib(sequence[SetUpScript], default=())
  tear_down = attrib(sequence[TearDownScript], default=())
  results_handler_name = attrib(
      enum(ALLOWED_RESULT_HANDLER_NAMES), default='default')
  isolate_coverage_data = attrib(bool, False)
  isolate_profile_data = attrib(bool, False)

  @property
  def test_class(self):
    """The test class associated with the spec."""
    return LocalIsolatedScriptTest


class LocalIsolatedScriptTest(LocalTest):

  def __init__(self, spec, chromium_tests_api):
    super(LocalIsolatedScriptTest, self).__init__(spec, chromium_tests_api)
    self._raw_cmd = []
    self._relative_cwd = None

  @property
  def raw_cmd(self):
    return self._raw_cmd

  @raw_cmd.setter
  def raw_cmd(self, value):
    self._raw_cmd = value

  @property
  def relative_cwd(self):
    return self._relative_cwd

  @relative_cwd.setter
  def relative_cwd(self, value):
    self._relative_cwd = value

  @property
  def set_up(self):
    return self.spec.set_up

  @property
  def tear_down(self):
    return self.spec.tear_down

  @property
  def isolate_target(self):
    return self.target_name

  @property
  def isolate_profile_data(self):
    # TODO(crbug.com/1075823) - delete isolate_coverage_data once deprecated
    # Release branches will still be setting isolate_coverage_data under
    # src/testing. Deprecation expected after M83.
    return self.spec.isolate_profile_data or self.spec.isolate_coverage_data

  def compile_targets(self):
    return self.spec.override_compile_targets or [self.spec.target_name]

  @Test.test_options.setter
  def test_options(self, value):
    self._test_options = value

  # TODO(nednguyen, kbr): figure out what to do with Android.
  # (crbug.com/533480)
  @recipe_api.composite_step
  def run(self, suffix):
    tests_to_retry = self._tests_to_retry(suffix)
    test_options = _test_options_for_running(self.test_options, suffix,
                                             tests_to_retry)
    pre_args = []
    if self.relative_cwd:
      pre_args += ['--relative-cwd', self.relative_cwd]

    cmd = list(self.raw_cmd)
    cmd.extend(self.spec.args)
    args = _merge_args_and_test_options(self, cmd, test_options)
    # TODO(nednguyen, kbr): define contract with the wrapper script to rerun
    # a subset of the tests. (crbug.com/533481)

    temp = self.api.m.path.mkstemp()
    json_results_file = self.api.m.json.output(leak_to=temp)
    args.extend(['--isolated-script-test-output', json_results_file])

    step_test_data = lambda: (
        self.api.m.json.test_api.output({
            'valid': True,
            'failures': []
        }) + self.api.m.raw_io.test_api.stream_output_text(
            'rdb-stream: included "invocations/test-name" in '
            '"invocations/build-inv"', 'stderr'))

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
                  '${ISOLATED_OUTDIR}/profraw/default-%1m.profraw',
          },
          # The results of the script will be isolated, and the .isolate will be
          # dumped to stdout.
          'stdout': self.api.m.raw_io.output_text(),
      })

    resultdb = self.prep_local_rdb(temp=temp)

    step_result = self.api.m.isolate.run_isolated(
        self.step_name(suffix),
        self.api.m.isolate.isolated_tests[self.target_name],
        args,
        pre_args=pre_args,
        step_test_data=step_test_data,
        raise_on_failure=False,
        resultdb=resultdb if resultdb else None,
        stderr=self.api.m.raw_io.output_text(
            add_output_log=True, name='stderr'),
        **kwargs)

    status = step_result.presentation.status

    self._suffix_step_name_map[suffix] = '.'.join(step_result.name_tokens)
    self.update_inv_name_from_stderr(step_result.stderr, suffix)
    self.update_failure_on_exit(suffix, step_result.retcode != 0)

    _present_info_messages(step_result.presentation, self)

    if step_result.retcode == 0 and not self.has_valid_results(suffix):
      # This failure won't be caught automatically. Need to manually
      # raise it as a step failure.
      raise self.api.m.step.StepFailure(
          self.api.m.test_utils.INVALID_RESULTS_MAGIC)

    return self.api.m.step.raise_on_failure(step_result, status)


@attrs()
class SwarmingIsolatedScriptTestSpec(SwarmingTestSpec):
  """Spec for a test that runs an isolated script via swarming.

  Attributes:
    * override_compile_targets - An optional list of compile targets to
      be built to run the test. If not provided the `target_name`
      attribute of the spec will be the only compile target.
    * results_handler_name - A name identifying the type of
      `ResultsHandler` that will be used for processing the test
      results:
      * 'default' - JSONResultsHandler
      * 'layout tests' - LayoutTestResultsHandler
      * 'fake' - FakeCustomResultsHandler
  """

  override_compile_targets = attrib(sequence[str], default=())
  results_handler_name = attrib(
      enum(ALLOWED_RESULT_HANDLER_NAMES), default='default')

  @property
  def test_class(self):
    """The test class associated with the spec."""
    return SwarmingIsolatedScriptTest


class SwarmingIsolatedScriptTest(SwarmingTest):

  def __init__(self, spec, chromium_tests_api):
    super(SwarmingIsolatedScriptTest, self).__init__(spec, chromium_tests_api)
    self._isolated_script_results = None

  def compile_targets(self):
    return self.spec.override_compile_targets or [self.target_name]

  @Test.test_options.setter
  def test_options(self, value):
    self._test_options = value

  def create_task(self, suffix, cas_input_root):
    task = self.api.m.chromium_swarming.isolated_script_task(
        raw_cmd=self.raw_cmd,
        relative_cwd=self.relative_cwd,
        cas_input_root=cas_input_root)

    self._apply_swarming_task_config(task, suffix,
                                     '--isolated-script-test-filter', '::')
    return task

  def validate_task_results(self, step_result):
    # Store the JSON results so we can later send them to the legacy
    # test-results service, but don't inspect/verify them at all.
    self._isolated_script_results = step_result.json.output
    return {}

  @recipe_api.composite_step
  def run(self, suffix):
    step_result = super(SwarmingIsolatedScriptTest, self).run(suffix)
    results = self._isolated_script_results

    if results:
      # Only version 3 of results is supported by the upload server.
      upload_step_name = '.'.join(step_result.name_tokens)
      if results and results.get('version', None) == 3:
        chrome_rev_cp = (
            self.api.m.bot_update.last_returned_properties.get(
                'got_revision_cp', 'refs/x@{#0}'))
        _, chrome_rev = self.api.m.commit_position.parse(str(chrome_rev_cp))
        self.api.m.test_results.upload(
            self.api.m.json.input(results),
            chrome_revision=str(chrome_rev),
            test_type=upload_step_name)
      if self.spec.results_handler_name == 'layout tests':
        _archive_layout_test_results(
            self.api.m, upload_step_name, step_suffix=suffix)
    return step_result


@attrs()
class AndroidJunitTestSpec(TestSpec):
  """Create a spec for a test that runs a Junit test on Android.

  Attributes:
    * additional_args - Additional arguments passed to the test.
  """

  compile_targets = attrib(sequence[str])
  additional_args = attrib(command_args, default=())

  @classmethod
  def create(cls, name, **kwargs):
    """Create an AndroidJunitTestSpec.

    Arguments:
      * name - The name of the test.
      * kwargs - Keyword arguments to initialize the attributes of the
        created object. The `compile_targets` attribute is fixed to the
        target name, so it cannot be specified.
    """
    target_name = kwargs.pop('target_name', None) or name
    return super(AndroidJunitTestSpec, cls).create(
        name, target_name=target_name, compile_targets=[target_name], **kwargs)

  @property
  def test_class(self):
    """The test class associated with the spec."""
    return AndroidJunitTest


class AndroidJunitTest(LocalTest):

  @property
  def uses_local_devices(self):
    return False

  #override
  def run_tests(self, suffix, json_results_file):
    step_test_data = lambda: (
        self.api.m.test_utils.test_api.canned_gtest_output(True) + self.api.m.
        raw_io.test_api.stream_output_text(
            'rdb-stream: included "invocations/test-name" in '
            '"invocations/build-inv"', 'stderr'))
    return self.api.m.chromium_android.run_java_unit_test_suite(
        self.name,
        target_name=self.spec.target_name,
        verbose=True,
        suffix=suffix,
        additional_args=self.spec.additional_args,
        json_results_file=json_results_file,
        step_test_data=step_test_data,
        stderr=self.api.m.raw_io.output_text(
            add_output_log=True, name='stderr'),
        resultdb=self.prep_local_rdb())

  @recipe_api.composite_step
  def run(self, suffix):
    assert self.api.m.chromium.c.TARGET_PLATFORM == 'android'

    json_results_file = self.api.m.test_utils.gtest_results(add_json_log=False)
    try:
      step_result = self.run_tests(suffix, json_results_file)
    except self.api.m.step.StepFailure as f:
      step_result = f.result
      raise
    finally:
      self._suffix_step_name_map[suffix] = '.'.join(step_result.name_tokens)
      self.update_inv_name_from_stderr(step_result.stderr, suffix)
      self.update_failure_on_exit(suffix, step_result.retcode != 0)

      _present_info_messages(step_result.presentation, self)

      presentation_step = self.api.m.step.empty('Report %s results' % self.name)
      gtest_results = (
          self.api.m.test_utils.present_gtest_failures(
              step_result, presentation=presentation_step.presentation))
      if gtest_results:
        self.api.m.test_results.upload(
            self.api.m.json.input(gtest_results.raw),
            test_type='.'.join(step_result.name_tokens),
            chrome_revision=self.api.m.bot_update.last_returned_properties.get(
                'got_revision_cp', 'refs/x@{#0}'))


    return step_result

  def compile_targets(self):
    return self.spec.compile_targets


@attrs()
class MockTestSpec(TestSpec):
  """Spec for a mock test.

  Attributes:
    * abort_on_failure - Whether the test should be aborted on failure.
    * failures - The test cases to report as failures.
    * has_valid_results - Whether the test has valid results.
    * per_suffix_failures - A mapping of suffix to the test cases to
      report as failures for the suffix.
    * per_suffix_valid - A mapping of suffix to whether the test has
      valid results for the suffix.
    * runs_on_swarming - Whether the test runs on swarming.
  """

  abort_on_failure = attrib(bool, default=False)
  failures = attrib(sequence[str], default=())
  has_valid_results = attrib(bool, default=True)
  per_suffix_failures = attrib(mapping[str, sequence[str]], default={})
  per_suffix_valid = attrib(mapping[str, bool], default={})
  runs_on_swarming = attrib(bool, default=False)

  @property
  def test_class(self):
    """The test class associated with the spec."""
    return MockTest


class MockTest(Test):
  """A Test solely intended to be used in recipe tests."""

  class ExitCodes(object):
    FAILURE = 1
    INFRA_FAILURE = 2

  def __init__(self, spec, chromium_tests_api):
    super(MockTest, self).__init__(spec, chromium_tests_api)
    # We mutate the set of failures depending on the exit code of the test
    # steps, so get a mutable copy
    self._failures = list(spec.failures)

  @property
  def runs_on_swarming(self):  # pragma: no cover
    return self.spec.runs_on_swarming

  @contextlib.contextmanager
  def _mock_exit_codes(self):
    try:
      yield
    except self.api.m.step.StepFailure as f:
      if f.result.retcode == self.ExitCodes.INFRA_FAILURE:
        i = self.api.m.step.InfraFailure(f.name, result=f.result)
        i.result.presentation.status = self.api.m.step.EXCEPTION
        raise i
      self._failures.append('test_failure')
      raise

  def pre_run(self, suffix):
    with self._mock_exit_codes():
      self.api.m.step('pre_run {}'.format(self.step_name(suffix)), None)

  @recipe_api.composite_step
  def run(self, suffix):
    with self._mock_exit_codes():
      try:
        step_result = self.api.m.step(self.step_name(suffix), None)
      finally:
        result = self.api.m.step.active_result
        self._suffix_step_name_map[suffix] = '.'.join(result.name_tokens)

    return step_result

  def has_valid_results(self, suffix):
    if suffix in self.spec.per_suffix_valid:  # pragma: no cover
      return self.spec.per_suffix_valid[suffix]
    return self.spec.has_valid_results

  def failures(self, suffix):
    if suffix in self.spec.per_suffix_failures:  # pragma: no cover
      return self.spec.per_suffix_failures[suffix]
    return self._failures

  def deterministic_failures(self, suffix):
    """Use same logic as failures for the Mock test."""
    return self.failures(suffix)

  def pass_fail_counts(self, suffix):
    return {}

  def compile_targets(self):  # pragma: no cover
    return []

  def get_invocation_names(self, _suffix):
    return []

  @property
  def abort_on_failure(self):
    return self.spec.abort_on_failure


# TODO(crbug.com/webrtc/12768): Delete this class once WebRTC has migrated
# off of it.
@attrs()
class SwarmingIosTestSpec(SwarmingTestSpec):
  """Spec for a test that runs against iOS via swarming.

  Attributes:
    * platform - The platform of the iOS target.
    * config - A dictionary detailing the build config. This is an
      ios-specific config that has no documentation.
    * task - A dictionary detailing the task config. This is an
      ios-specific config that has no documentation.
    * upload_test_results - Whether or not test results should be
      uploaded.
    * result_callback - A callback to run whenever a task finishes. It
      is called with these named args:
      * name: Name of the test ('test'->'app' attribute)
      * step_result: Step result object from the collect step.
      If the callback is not provided, the default is to upload
      performance results from perf_result.json
    * use_rdb - True if the tests results are to be uploaded to ResultDB.
    * xcode_app_path - Swarming named cache path for the test's XCode.
  """

  platform = attrib(enum(['device', 'simulator']), default=None)
  config = attrib(mapping[str, ...], default={})
  task = attrib(mapping[str, ...], default={})
  upload_test_results = attrib(bool, default=False)
  result_callback = attrib(callable_, default=None)
  use_rdb = attrib(bool, default=False)
  xcode_app_path = attrib(str, default=None)

  @classmethod
  def create(  # pylint: disable=arguments-differ
      cls, platform, config, task, **kwargs):
    """Create a SwarmingIosTestSpec.

    A number of attributes in the returned spec are either extracted
    from `task` or `config` or are based on the value of `platform`
    and/or values in 'task' and/or 'config'.

    Arguments:
      * platform - The platform of the iOS target.
      * config - A dictionary detailing the build config.
      * task - A dictionary detailing the task config.
      * kwargs - Additional keyword arguments that will be used to
        initialize the attributes of the returned spec.
    """
    return super(SwarmingIosTestSpec, cls).create(
        name=task['step name'],
        platform=platform,
        config=config,
        task=task,
        cipd_packages=cls._get_cipd_packages(task),
        expiration=(task['test'].get('expiration_time') or
                    config.get('expiration_time')),
        hard_timeout=(task['test'].get('max runtime seconds') or
                      config.get('max runtime seconds')),
        dimensions=cls._get_dimensions(platform, config, task),
        optional_dimensions=task['test'].get('optional_dimensions'),
        **kwargs)

  @staticmethod
  def _get_cipd_packages(task):
    cipd_packages = [
        chromium_swarming.CipdPackage.create(
            name=MAC_TOOLCHAIN_PACKAGE,
            version=MAC_TOOLCHAIN_VERSION,
            root=MAC_TOOLCHAIN_ROOT,
        )
    ]

    replay_package_name = task['test'].get('replay package name')
    replay_package_version = task['test'].get('replay package version')
    use_trusted_cert = task['test'].get('use trusted cert')
    if use_trusted_cert or (replay_package_name and replay_package_version):
      cipd_packages.append(
          chromium_swarming.CipdPackage.create(
              name=WPR_TOOLS_PACKAGE,
              version=WPR_TOOLS_VERSION,
              root=WPR_TOOLS_ROOT,
          ))
    if replay_package_name and replay_package_version:
      cipd_packages.append(
          chromium_swarming.CipdPackage.create(
              name=replay_package_name,
              version=replay_package_version,
              root=WPR_REPLAY_DATA_ROOT,
          ))

    return cipd_packages

  @staticmethod
  def _get_dimensions(platform, config, task):
    dimensions = {
        'pool': 'chromium.tests',
    }

    # TODO(crbug.com/835036): remove this when all configs are migrated to
    # "xcode build version". Otherwise keep it for backwards compatibility;
    # otherwise we may receive an older Mac OS which does not support the
    # requested Xcode version.
    if task.get('xcode version'):
      dimensions['xcode_version'] = task['xcode version']

    if platform == 'simulator':
      # TODO(crbug.com/955856): We should move away from 'host os'.
      dimensions['os'] = task['test'].get('host os') or 'Mac'
    elif platform == 'device':
      dimensions['os'] = 'iOS-%s' % str(task['test']['os'])
      if config.get('device check'):
        dimensions['device_status'] = 'available'
      dimensions['device'] = IOS_PRODUCT_TYPES.get(task['test']['device type'])
    if task['bot id']:
      dimensions['id'] = task['bot id']
    if task['pool']:
      dimensions['pool'] = task['pool']

    return dimensions

  @property
  def test_class(self):
    """The test class associated with the spec."""
    return SwarmingIosTest


# TODO(crbug.com/webrtc/12768): Delete this class once WebRTC has migrated
# off of it.
class SwarmingIosTest(SwarmingTest):

  def __init__(self, spec, chromium_tests_api):
    super(SwarmingIosTest, self).__init__(spec, chromium_tests_api)

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

    # A map from suffix [e.g. 'with patch'] to the name of the recipe engine
    # step that was invoked in run(). This makes the assumption that run() only
    # emits a single recipe engine step, and that the recipe engine step is the
    # one that best represents the run of the tests. This is used by FindIt to
    # look up the failing step for a test suite from buildbucket.
    self._suffix_step_name_map = {}

  def has_valid_results(self, suffix):
    return self._test_runs[suffix]['valid']

  def deterministic_failures(self, suffix):
    """Return tests that failed on every test run(list of strings)."""
    failure_msg = (
        'There is no data for the test run suffix ({0}). This should never '
        'happen as all calls to deterministic_failures() should first check '
        'that the data exists.'.format(suffix))
    assert suffix in self._deterministic_failures, failure_msg
    return self._deterministic_failures[suffix]

  def update_test_run(self, suffix, test_run):
    self._test_runs[suffix] = test_run
    self._deterministic_failures[suffix] = (
        self.api.m.test_utils.canonical.deterministic_failures(
            self._test_runs[suffix]))

  def pre_run(self, suffix):
    task = self.spec.task

    task_output_dir = self.api.m.path.mkdtemp(task['task_id'])
    raw_cmd = task.get('raw_cmd')
    if raw_cmd is not None:
      raw_cmd = list(raw_cmd)

    swarming_task = self.api.m.chromium_swarming.task(
        name=task['step name'],
        task_output_dir=task_output_dir,
        failure_as_exception=False,
        relative_cwd=task.get('relative_cwd'),
        cas_input_root=task['task input'],
        raw_cmd=raw_cmd)

    self._apply_swarming_task_config(
        swarming_task, suffix, filter_flag=None, filter_delimiter=None)

    task_slice = swarming_task.request[0]

    # The implementation of _apply_swarming_task_config picks up default
    # dimensions which don't work for iOS because the swarming bots do not
    # specify typical dimensions [GPU, cpu type]. We explicitly override
    # dimensions here to get the desired results.
    task_slice = task_slice.with_dimensions(**self.spec.dimensions)
    swarming_task.request = (
        swarming_task.request.with_slice(0, task_slice).with_priority(
            task['test'].get('priority', 200)))

    if self.spec.platform == 'device' and self.spec.config.get('device check'):
      swarming_task.wait_for_capacity = True

    assert task.get('xcode build version')
    named_cache = 'xcode_ios_%s' % (task['xcode build version'])
    swarming_task.named_caches[named_cache] = self.spec.xcode_app_path

    if self.spec.platform == 'simulator':
      runtime_cache_name = 'runtime_ios_%s' % str(task['test']['os']).replace(
          '.', '_')
      runtime_cache_path = 'Runtime-ios-%s' % str(task['test']['os'])
      swarming_task.named_caches[runtime_cache_name] = runtime_cache_path

    swarming_task.tags.add('device_type:%s' % str(task['test']['device type']))
    swarming_task.tags.add('ios_version:%s' % str(task['test']['os']))
    swarming_task.tags.add('platform:%s' % self.spec.platform)
    swarming_task.tags.add('test:%s' % str(task['test']['app']))

    resultdb = self.spec.resultdb if self.spec.use_rdb else None
    self.api.m.chromium_swarming.trigger_task(swarming_task, resultdb)
    self._tasks[suffix] = swarming_task

  @recipe_api.composite_step
  def run(self, suffix):
    task = self.spec.task
    swarming_task = self._tasks[suffix]

    assert swarming_task, ('The task should have been triggered and have an '
                           'associated swarming task')

    step_result, has_valid_results = (
        self.api.m.chromium_swarming.collect_task(swarming_task))
    self._suffix_step_name_map[suffix] = '.'.join(step_result.name_tokens)

    # Add any iOS test runner results to the display.
    shard_output_dir = swarming_task.get_task_shard_output_dirs()[0]
    test_summary_path = self.api.m.path.join(shard_output_dir, 'summary.json')

    if test_summary_path in step_result.raw_io.output_dir:
      test_summary_json = self.api.m.json.loads(
          step_result.raw_io.output_dir[test_summary_path])

      logs = test_summary_json.get('logs', {})
      passed_tests = logs.get('passed tests', [])
      flaked_tests = logs.get('flaked tests', [])
      failed_tests = logs.get('failed tests', [])

      # The iOS test runners will not always emit 'failed tests' or any other
      # signal on certain types of errors. This is a test runner bug but we add
      # a workaround here. https:/crbug.com/958791.
      if swarming_task.failed_shards and not failed_tests:
        failed_tests = ['invalid test results']

      pass_fail_counts = collections.defaultdict(lambda: {
          'pass_count': 0,
          'fail_count': 0
      })
      for test in passed_tests:
        pass_fail_counts[test]['pass_count'] += 1
      for test in flaked_tests:
        pass_fail_counts[test]['pass_count'] += 1
        pass_fail_counts[test]['fail_count'] += 1
      for test in failed_tests:
        pass_fail_counts[test]['fail_count'] += 1
      test_count = len(passed_tests) + len(flaked_tests) + len(failed_tests)
      canonical_results = (
          self.api.m.test_utils.canonical.result_format(
              valid=has_valid_results,
              failures=failed_tests,
              total_tests_ran=test_count,
              pass_fail_counts=pass_fail_counts))
      self.update_test_run(suffix, canonical_results)

      step_result.presentation.logs['test_summary.json'] = (
          self.api.m.json.dumps(test_summary_json, indent=2).splitlines())
      step_result.presentation.logs.update(
          self.api.m.py3_migration.consistent_ordering(six.iteritems(logs)))
      step_result.presentation.links.update(test_summary_json.get('links', {}))
      if test_summary_json.get('step_text'):
        step_result.presentation.step_text = '%s<br />%s' % (
            step_result.presentation.step_text, test_summary_json['step_text'])
    else:
      self.update_test_run(suffix,
                           self.api.m.test_utils.canonical.result_format())
    self.update_failure_on_exit(suffix, bool(swarming_task.failed_shards))

    # Upload test results JSON to the flakiness dashboard.
    shard_output_dir_full_path = self.api.m.path.join(
        swarming_task.task_output_dir,
        swarming_task.get_task_shard_output_dirs()[0])
    if (self.api.m.bot_update.last_returned_properties and
        self.spec.upload_test_results):
      test_results = self.api.m.path.join(shard_output_dir_full_path,
                                          'full_results.json')
      if self.api.m.path.exists(test_results):
        self.api.m.test_results.upload(
            test_results,
            '.'.join(step_result.name_tokens),
            self.api.m.bot_update.last_returned_properties.get(
                'got_revision_cp', 'refs/x@{#0}'),
            builder_name_suffix='%s-%s' %
            (task['test']['device type'], task['test']['os']),
            test_results_server='test-results.appspot.com',
        )

    # Upload performance data result to the perf dashboard.
    perf_results_path = self.api.m.path.join(shard_output_dir, 'Documents',
                                             'perf_result.json')
    if self.spec.result_callback:
      self.spec.result_callback(
          name=task['test']['app'], step_result=step_result)
    elif perf_results_path in step_result.raw_io.output_dir:
      data = self.api.m.json.loads(
          step_result.raw_io.output_dir[perf_results_path])
      data_decode = data['Perf Data']
      data_result = []
      for testcase in data_decode:
        for trace in data_decode[testcase]['value']:
          data_point = (
              self.api.m.perf_dashboard.get_skeleton_point(
                  'chrome_ios_perf/%s/%s' % (testcase, trace),
                  # TODO(huangml): Use revision.
                  int(self.api.m.time.time()),
                  data_decode[testcase]['value'][trace]))
          data_point['units'] = data_decode[testcase]['unit']
          data_result.extend([data_point])
      self.api.m.perf_dashboard.set_default_config()
      self.api.m.perf_dashboard.add_point(data_result)

    return step_result

  def validate_task_results(self, step_result):
    raise NotImplementedError()  # pragma: no cover

  def create_task(self, suffix, task_input):
    raise NotImplementedError()  # pragma: no cover

  def compile_targets(self):
    raise NotImplementedError()  # pragma: no cover


@attrs()
class SkylabTestSpec(TestSpec):
  """Spec for a suite that runs on CrOS Skylab."""
  cros_board = attrib(str)
  cros_img = attrib(str)
  secondary_cros_board = attrib(str, default='')
  secondary_cros_img = attrib(str, default='')
  dut_pool = attrib(str, default='')
  tast_expr = attrib(str, default='')
  test_args = attrib(command_args, default=())
  autotest_name = attrib(str, default='')
  timeout_sec = attrib(int, default=3600)
  # Enable retry for all Skylab tests by default. We see around 10% of tests
  # failed due to lab issues. Set retry into test requests, so that failed
  # tests could get rerun from OS infra side. We only bridged our CI builders
  # to Skylab now, so we do not expect a lot of failures from our artifact.
  # Revisit this when we integrate CQ to Skylab.
  retries = attrib(int, default=3)

  @classmethod
  def create(cls, name, **kwargs):
    """Create a SkylabTestSpec.

    Arguments:
      * name - The name of the test.
      * kwargs - Keyword arguments to initialize the attributes of the
        SkylabTestSpec.
    """
    rdb_kwargs = kwargs.pop('resultdb', {})
    return super(SkylabTestSpec, cls).create(
        name, resultdb=ResultDB.create(**rdb_kwargs), **kwargs)

  @property
  def test_class(self):
    return SkylabTest


class SkylabTest(Test):

  def __init__(self, spec, chromium_tests_api):
    super(SkylabTest, self).__init__(spec, chromium_tests_api)
    # cros_test_platform build, aka CTP is the entrance for the CrOS hardware
    # tests, which kicks off test_runner builds for our test suite.
    # Each test suite has a CTP build ID, as long as the buildbucket call is
    # successful.
    self.ctp_build_id = 0
    # test_runner build represents the test execution in Skylab. Tests can be
    # retried, so multiple runs are possible.
    # If CTP failed to schedule test runners, this list could be empty. Use
    # ctp_build_id to troubleshoot.
    self.test_runner_builds = []
    self.lacros_gcs_path = None
    self.exe_rel_path = None

  @property
  def is_skylabtest(self):
    return True

  @property
  def is_tast_test(self):
    return bool(self.spec.tast_expr)

  @property
  def skylab_req(self):
    return SkylabRequest.create(
        request_tag=self.name,
        tast_expr=self.spec.tast_expr,
        test_args=' '.join(self.spec.test_args),
        autotest_name=self.spec.autotest_name,
        board=self.spec.cros_board,
        cros_img=self.spec.cros_img,
        secondary_board=self.spec.secondary_cros_board,
        secondary_cros_img=self.spec.secondary_cros_img,
        dut_pool=self.spec.dut_pool,
        lacros_gcs_path=self.lacros_gcs_path,
        exe_rel_path=self.exe_rel_path,
        timeout_sec=self.spec.timeout_sec,
        retries=self.spec.retries,
        resultdb=self.prep_skylab_rdb(),
    ) if self.lacros_gcs_path else None

  def _raise_failed_step(self, suffix, step, status, failure_msg):
    step.presentation.status = status
    step.presentation.step_text += failure_msg
    self.update_failure_on_exit(suffix, True)
    raise self.api.m.step.StepFailure(status)

  def prep_skylab_rdb(self):
    var = dict(
        self.spec.resultdb.base_variant or {}, test_suite=self.canonical_name)
    var.update({
        'device_type': self.spec.cros_board,
        'os': 'ChromeOS',
        'cros_img': self.spec.cros_img,
    })
    return attr.evolve(
        self.spec.resultdb,
        test_id_prefix=self.spec.test_id_prefix,
        base_variant=var,
        result_format='tast' if self.is_tast_test else 'gtest',
        # Skylab's result_file is hard-coded by the autotest wrapper in OS
        # repo, and not required by callers. It suppose to be None, but then
        # ResultDB will pass the default value ${ISOLATED_OUTDIR}/output.json
        # which is confusing for Skylab test runner. So explicitly set it an
        # empty string, as well as artifact_directory.
        result_file='',
        # Tast adapter is designed mostly for Skylab, so it collects the
        # artifact for us. No need to configure any path, plus we do not
        # know the runtime path of the artifact on the host server in Skylab.
        # For gtest, we have to explicitly set the relative path of artifacts
        # to the adapter.
        artifact_directory='' if self.is_tast_test else 'chromium/debug')

  def get_invocation_names(self, suffix):
    # TODO(crbug.com/1248693): Use the invocation included by the parent builds.
    del suffix
    inv_names = []
    for b in self.test_runner_builds:
      inv_names.append('invocations/build-%d' % b.id)
    return inv_names

  @recipe_api.composite_step
  def run(self, suffix):
    self._suffix_step_name_map[suffix] = self.step_name(suffix)
    bb_url = 'https://ci.chromium.org/b/%d'

    with self.api.m.step.nest(self.step_name(suffix)) as step:
      _present_info_messages(step, self)
      if not self.lacros_gcs_path:
        self._raise_failed_step(
            suffix, step, self.api.m.step.FAILURE,
            'Test was not scheduled because of absent lacros_gcs_path.')

      rdb_results = self._rdb_results.get(suffix)
      if rdb_results.total_tests_ran:
        # If any test result was reported by RDB, the test run completed
        # its lifecycle as expected.
        self.update_failure_on_exit(suffix, False)
      else:
        step.links['CTP Build'] = bb_url % self.ctp_build_id
        self._raise_failed_step(
            suffix, step, self.api.m.step.EXCEPTION,
            'Test did not run or failed to report to ResultDB.'
            'Check the CTP build for details.')

      if rdb_results.unexpected_failing_tests:
        step.presentation.status = self.api.m.step.FAILURE
      self.present_rdb_results(step, rdb_results)

      if len(self.test_runner_builds) == 1:
        step.links['Test Run'] = bb_url % self.test_runner_builds[0].id
      else:
        self.test_runner_builds.sort(key=lambda b: b.create_time.seconds)
        for i, b in enumerate(self.test_runner_builds):
          with self.api.m.step.nest('attempt: #' + str(i + 1)) as attempt_step:
            attempt_step.links['Test Run'] = bb_url % b.id
            if b.status == common_pb2.INFRA_FAILURE:
              attempt_step.presentation.status = (self.api.m.step.EXCEPTION)
            elif b.status == common_pb2.FAILURE:
              attempt_step.presentation.status = (self.api.m.step.FAILURE)
        # If the status of any test run is success, the parent step should be
        # success too. The "Test Results" tab could expose the detailed flaky
        # information.
        if any(
            [b.status == common_pb2.SUCCESS for b in self.test_runner_builds]):
          step.presentation.status = self.api.m.step.SUCCESS
          step.presentation.step_text = (
              'Test had failed runs. '
              'Check "Test Results" tab for the deterministic results.')

    return step

  def compile_targets(self):
    t = [self.spec.target_name]
    if self.is_tast_test:
      t.append('chrome')
    return t
