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
import datetime
import hashlib
import json
import re
import string
import struct
import urllib
import urlparse

from recipe_engine import recipe_api
from recipe_engine.config_types import Path
from recipe_engine.types import freeze
from recipe_engine.types import FrozenDict
from recipe_engine.util import Placeholder

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2

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
# https://chromium.googlesource.com/infra/infra/+/master/go/src/infra/cmd/mac_toolchain
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


def _merge_args_and_test_options(test, args, options):
  """Adds args from test options.

  Args:
    test: A test suite. An instance of a subclass of Test.
    args: The list of args of extend.
    options: The TestOptions to use to extend args.

  Returns:
    The extended list of args.
  """
  args = list(args)

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


def _add_suffix(step_name, suffix):
  if not suffix:
    return step_name
  return '{} ({})'.format(step_name, suffix)


@attrs()
class ResultDB(object):
  """Configuration for ResultDB-integration for a test.

  Attributes:
    * enable - Whether or not ResultDB-integration is enabled.
    * result_format - The format of the test results.
    * test_id_as_test_location - Whether the test ID will be used as the
      test location. It only makes sense to set this for blink_web_tests
      and webgl_conformance_tests.
    * test_location_base - File base to prepend to the test location
      file name, if the file name is a relative path. It must start with
      "//".
    * base_tags - Tags to attach to all test results by default. Each element
      is (key, value), and a key may be repeated.
    * base_variant - Dict of Variant key-value pairs to attach to all test
      results by default.
    * test_id_prefix - Prefix to prepend to test IDs of all test results.
    * coerce_negative_duration - If True, negative duration values will
      be coerced to 0. If false, tests results with negative duration values
      will be rejected with an error.
    * result_file - path to result file for result_adapter to read test results
      from. It is meaningful only when result_format is not None.
    * artifact_directory - path to artifact directory where result_adapter
      finds and uploads artifacts from.
    * location_tags_file - path to the location tags file for ResultSink to read
      and attach location based tags to each test result.
    * exonerate_unexpected_pass - flag to control if ResultSink should
      automatically exonerate unexpected passes.
    * result_adapter_path - path to result_adapter binary.
    * include - If True, a new invocation will be created for the test and
      included in the parent invocation.
  """
  enable = attrib(bool, default=False)
  result_format = attrib(enum(['gtest', 'json', 'single']), default=None)
  test_id_as_test_location = attrib(bool, default=False)
  test_location_base = attrib(str, default=None)
  base_tags = attrib(sequence[tuple], default=None)
  base_variant = attrib(mapping[str, str], default=None)
  coerce_negative_duration = attrib(bool, default=True)
  test_id_prefix = attrib(str, default='')
  result_file = attrib(str, default='${ISOLATED_OUTDIR}/output.json')
  artifact_directory = attrib((str, Placeholder), default='${ISOLATED_OUTDIR}')
  location_tags_file = attrib(str, default=None)
  exonerate_unexpected_pass = attrib(bool, default=True)
  include = attrib(bool, default=False)
  # result_adapter binary is available in chromium checkout or
  # the swarming bot.
  #
  # local tests can use it from chromium checkout with the following path
  # : $CHECKOUT/src/tools/resultdb/result_adapter
  #
  # However, swarmed tasks can't use it, because there is no guarantee that
  # the isolate would include result_adapter always. Instead, swarmed tasks use
  # result_adapter deployed via the pool config. That is, result_adapter
  # w/o preceding path.
  result_adapter_path = attrib(str, default='result_adapter')

  @classmethod
  def create(cls, **kwargs):
    """Create a ResultDB instance.

    Args:
      * kwargs - Keyword arguments to initialize the attributes of the
        created object.

    Returns:
      If True was passed for keyword argument `enable`, a `ResultDB`
      instance with attributes initialized with the matching keyword
      arguments. Otherwise, a default `ResultDB` instance (validity of
      the keyword arguments will still be checked).
    """
    # Unconditionally construct an instance with the keywords to have the
    # arguments validated.
    resultdb = cls(**kwargs)
    if not resultdb.enable:
      return cls()
    return resultdb

  def wrap(self,
           api,
           cmd,
           step_name=None,
           base_variant=None,
           base_tags=None,
           require_build_inv=True,
           **kwargs):
    """Wraps the cmd with ResultSink and result_adapter, if conditions are met.

    This function enables resultdb for a given command by wrapping it with
    ResultSink and result_adapter, based on the config values set in ResultDB
    instance. Find the config descriptions for more info.

    If config values are passed as params, they override the values set in
    the ResultDB object.

    Args:
      * api - Recipe API object.
      * cmd - List with the test command and arguments to wrap with ResultSink
        and result_adapter.
      * step_name - Step name to add as a tag to each test result.
      * base_variant - Dict of variants to add to base_variant.
        If there are duplicate keys, the new variant value wins.
      * base_tags - List of tags to add to base_tags.
      * require_build_inv - flag to control if the build is required to have
        an invocation.
      * kwargs - Overrides for the rest of ResultDB attrs.
    """
    assert isinstance(cmd, (tuple, list)), "%s: %s" % (step_name, cmd)
    assert isinstance(step_name, (type(None), str)), "%s: %s" % (step_name, cmd)
    configs = attr.evolve(self, **kwargs)
    if not configs.enable:
      return cmd

    # wrap it with result_adapter
    if configs.result_format:
      exe = configs.result_adapter_path + ('.exe'
                                           if api.platform.is_win else '')
      result_adapter = [
          exe,
          configs.result_format,
          '-result-file',
          configs.result_file,
      ]
      if configs.artifact_directory:
        result_adapter += ['-artifact-directory', configs.artifact_directory]

      if configs.result_format == 'json' and configs.test_id_as_test_location:
        result_adapter += ['-test-location']

      cmd = result_adapter + ['--'] + list(cmd)

    # add var 'builder' by default
    var = {'builder': api.buildbucket.builder_name}
    var.update(self.base_variant or {})
    var.update(base_variant or {})

    tags = set(base_tags or [])
    tags.update(self.base_tags or [])
    if step_name:
      tags.add(('step_name', step_name))

    # wrap it with rdb-stream
    return api.resultdb.wrap(
        cmd,
        base_tags=list(tags),
        base_variant=var,
        coerce_negative_duration=configs.coerce_negative_duration,
        test_id_prefix=configs.test_id_prefix,
        test_location_base=configs.test_location_base,
        location_tags_file=configs.location_tags_file,
        require_build_inv=require_build_inv,
        exonerate_unexpected_pass=configs.exonerate_unexpected_pass,
        include=configs.include,
    )


class TestSpecBase(object):
  """Abstract base class for specs for tests and wrapped tests."""

  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def get_test(self):
    """Get a test instance described by the spec.

    Returns:
      An instance of either a `Test` subclass or an instance of a
      `TestWrapper` subclass.
    """
    raise NotImplementedError()  # pragma: no cover

  @abc.abstractmethod
  def without_waterfall(self):
    """Get a spec without any waterfall specified.

    Specs created manually in recipes will most likely not have the
    waterfall specified, so this provides a means of comparing the
    actual values of concern during migration.
    """
    raise NotImplementedError()  # pragma: no cover

  @abc.abstractmethod
  def without_test_id_prefix(self):
    """Get a spec without any test ID prefix specified.

    Specs created manually in recipes will most likely not have the
    test ID prefix specified, so this provides a means of comparing the
    actual values of concern during migration.
    """
    raise NotImplementedError()  # pragma: no cover

  @abc.abstractmethod
  def without_merge(self):
    """Get a spec without any merge script specified.

    Specs created manually in recipes will most likely not have the
    merge script specified, so this provides a means of comparing the
    actual values of concern during migration.
    """
    raise NotImplementedError()  # pragma: no cover

  @abc.abstractmethod
  def as_jsonish(self):
    """Convert the spec to a JSON-representable equivalent dict."""
    raise NotImplementedError()  # pragma: no cover


@attrs()
class TestSpec(TestSpecBase):
  """Abstract base class for specs for tests.

  Attributes:
    * name - The displayed name of the test.
    * target_name - The ninja build target for the test, a key in
      //testing/buildbot/gn_isolate_map.pyl, e.g. "browser_tests".
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

  def get_test(self):
    """Get the test described by the spec."""
    return self.test_class(self)

  def without_waterfall(self):
    return attr.evolve(
        self, waterfall_builder_group=None, waterfall_buildername=None)

  def without_test_id_prefix(self):
    return attr.evolve(self, test_id_prefix=None)

  def without_merge(self):
    return self  # pragma: no cover

  def as_jsonish(self):
    d = attr.asdict(self)
    d['_spec_type'] = type(self).__name__
    return d


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

  def __init__(self, spec):
    super(Test, self).__init__()

    self.spec = spec

    self._test_options = TestOptions()

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

    # A map from suffix [e.g. 'with patch'] to the name of the recipe engine
    # step that was invoked in run(). This makes the assumption that run() only
    # emits a single recipe engine step, and that the recipe engine step is the
    # one that best represents the run of the tests. This is used by FindIt to
    # look up the failing step for a test suite from buildbucket.
    self._suffix_step_name_map = {}

    # Used to track results of tests as reported by RDB. Separate from
    # _deterministic_failures above as that is populated by parsing the tests'
    # JSON results, while this field is populated entirely by RDB's API. Note
    # that this field is only populated for SwarmingTests, but is initialized
    # here for compatibility reasons. Also keyed via suffix like
    # _deterministic_failures above.
    self._rdb_results = {}

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
    """Returns isolate target name. Defaults to name."""
    return self.target_name

  @property
  def is_gtest(self):
    return False

  @property
  def is_skylabtest(self):
    return False

  @property
  def runs_on_swarming(self):
    return False

  def prep_local_rdb(self, api, temp=None, include_artifacts=True):
    """Returns a ResultDB instance suitable for local test runs.

    Main difference between remote swarming runs and local test runs (ie:
    ScriptTests and LocalIsolatedScriptTests) is the location of a temp
    result file and the location of the result_adapter binary.

    Args:
      api: Recipe API object.
      temp: Path to temp file to store results.
      include_artifacts: If True, add the parent dir of temp as an artifact dir.
    """
    temp = temp or api.path.mkstemp()
    artifact_dir = api.path.dirname(temp) if include_artifacts else ''
    resultdb = attr.evolve(
        self.spec.resultdb,
        artifact_directory=artifact_dir,
        base_variant=dict(
            self.spec.resultdb.base_variant or {},
            test_suite=self.canonical_name),
        result_adapter_path=str(api.path['checkout'].join(
            'tools', 'resultdb', 'result_adapter')),
        result_file=api.path.abspath(temp),
        # Give each local test suite its own invocation to make it easier to
        # fetch results.
        include=True)
    return resultdb

  def get_invocation_names(self, _suffix):  # pragma: no cover
    """Returns the invocation names tracking the test's results in RDB."""
    # TODO(crbug.com/1135718): Raise a NotImplementedError once all subclasses
    # have an implementation.
    return []

  @property
  def rdb_results(self):
    return self._rdb_results

  def update_rdb_results(self, suffix, results):
    self._rdb_results[suffix] = results

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
    return int(
        min(
            min(
                max(
                    original_num_shards * REPEAT_COUNT_FOR_FAILING_TESTS *
                    (float(num_tests_to_retry) / total_tests_ran), 1),
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
    for test_name, result in (self.pass_fail_counts(suffix).iteritems()):
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

  def get_test(self):
    """Get the test described by the spec."""
    return self.test_wrapper_class(self, self.test_spec.get_test())

  @abc.abstractproperty
  def test_wrapper_class(self):
    """The test wrapper class associated with the spec."""
    raise NotImplementedError()  # pragma: no cover

  @property
  def name(self):
    """The name of the test."""
    return self.test_spec.name

  def without_waterfall(self):
    return attr.evolve(self, test_spec=self.test_spec.without_waterfall())

  def without_test_id_prefix(self):
    return attr.evolve(self, test_spec=self.test_spec.without_test_id_prefix())

  def without_merge(self):
    return attr.evolve(self, test_spec=self.test_spec.without_merge())

  def as_jsonish(self):

    def attribute_filter(attribute, value):
      del value
      return attribute.name != 'test_spec'

    d = attr.asdict(self, filter=attribute_filter)
    d['_spec_type'] = type(self).__name__
    d['test_spec'] = self.test_spec.as_jsonish()
    return d


class TestWrapper(Test):  # pragma: no cover
  """ A base class for Tests that wrap other Tests.

  By default, all functionality defers to the wrapped Test.
  """

  def __init__(self, spec, test):
    super(TestWrapper, self).__init__(test.name)
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

  @property
  def is_gtest(self):
    return self._test.is_gtest

  def compile_targets(self):
    return self._test.compile_targets()

  def name_of_step_for_suffix(self, suffix):
    return self._test.name_of_step_for_suffix(suffix)

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


@attrs()
class ExperimentalTestSpec(TestWrapperSpec):
  """A spec for a test to be executed at some percentage.

  Attributes:
    * experiment_percentage - The percentage chance that the test will
      be executed.
    * is_in_experiment - Whether or not the test is in the experiment.
  """

  # TODO(gbeaty) This field exists just for comparison while tracking test specs
  # migrations, once all specs are migrated source-side it can be removed.
  experiment_percentage = attrib(int)
  is_in_experiment = attrib(bool)

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
    return super(ExperimentalTestSpec, cls).create(
        test_spec,
        experiment_percentage=experiment_percentage,
        is_in_experiment=is_in_experiment)

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

    digest = hashlib.sha1(''.join(str(c) for c in criteria)).digest()
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

  def _is_in_experiment_and_has_valid_results(self, suffix):
    return (self.spec.is_in_experiment and
            super(ExperimentalTest, self).has_valid_results(
                self._experimental_suffix(suffix)))

  @property
  def abort_on_failure(self):
    return False

  #override
  def pre_run(self, api, suffix):
    if not self.spec.is_in_experiment:
      return []

    try:
      return super(ExperimentalTest,
                   self).pre_run(api, self._experimental_suffix(suffix))
    except api.step.StepFailure:
      pass

  #override
  def name_of_step_for_suffix(self, suffix):
    # Wraps the parent method since we use a modified suffix internally.
    if not self.spec.is_in_experiment:
      return None  # If the experiment isn't on, there won't be any step.
    experimental_suffix = self._experimental_suffix(suffix)
    return super(ExperimentalTest,
                 self).name_of_step_for_suffix(experimental_suffix)

  #override
  @recipe_api.composite_step
  def run(self, api, suffix):
    if not self.spec.is_in_experiment:
      return []

    try:
      return super(ExperimentalTest,
                   self).run(api, self._experimental_suffix(suffix))
    except api.step.StepFailure:
      pass

  #override
  def has_valid_results(self, suffix):
    if self.spec.is_in_experiment:
      # Call the wrapped test's implementation in case it has side effects,
      # but ignore the result.
      super(ExperimentalTest,
            self).has_valid_results(self._experimental_suffix(suffix))
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
      super(ExperimentalTest,
            self).deterministic_failures(self._experimental_suffix(suffix))
    return []

  #override
  def findit_notrun(self, suffix):  # pragma: no cover
    if self._is_in_experiment_and_has_valid_results(suffix):
      # Call the wrapped test's implementation in case it has side effects,
      # but ignore the result.
      super(ExperimentalTest,
            self).findit_notrun(self._experimental_suffix(suffix))
    return set()

  def pass_fail_counts(self, suffix):
    if self._is_in_experiment_and_has_valid_results(suffix):
      # Call the wrapped test's implementation in case it has side effects,
      # but ignore the result.
      super(ExperimentalTest,
            self).pass_fail_counts(self._experimental_suffix(suffix))
    return {}


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


class ScriptTest(Test):  # pylint: disable=W0232
  """
  Test which uses logic from script inside chromium repo.

  This makes it possible to keep the logic src-side as opposed
  to the build repo most Chromium developers are unfamiliar with.

  Another advantage is being to test changes to these scripts
  on trybots.

  All new tests are strongly encouraged to use this infrastructure.
  """

  def __init__(self, spec):
    super(ScriptTest, self).__init__(spec)
    self._suffix_to_invocation_names = {}

  def get_invocation_names(self, suffix):
    inv = self._suffix_to_invocation_names.get(suffix)
    return [inv] if inv else []

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
  def run(self, api, suffix):
    run_args = []

    tests_to_retry = self._tests_to_retry(suffix)
    if tests_to_retry:
      run_args.extend(['--filter-file',
                       api.json.input(tests_to_retry)])  # pragma: no cover

    result = None
    try:
      resultdb = self.prep_local_rdb(api)

      script_args = []
      if self.spec.script_args:
        script_args = ['--args', api.json.input(self.spec.script_args)]
      api.build.python(
          self.step_name(suffix),
          # Enforce that all scripts are in the specified directory
          # for consistency.
          api.path['checkout'].join('testing', 'scripts',
                                    api.path.basename(self.spec.script)),
          args=(api.chromium_tests.get_common_args_for_scripts() + script_args +
                ['run', '--output', api.json.output()] + run_args),
          resultdb=resultdb if resultdb else None,
          stderr=api.raw_io.output(add_output_log=True, name='stderr'),
          venv=True,  # Runs the test through vpython.
          step_test_data=lambda: api.json.test_api.output({
              'valid': True,
              'failures': []
          }))
    finally:
      result = api.step.active_result
      self._suffix_step_name_map[suffix] = '.'.join(result.name_tokens)

      failures = None
      if result.json.output:
        failures = result.json.output.get('failures')
      if failures is None:
        self.update_test_run(api, suffix,
                             api.test_utils.canonical.result_format())
        api.python.failing_step(
            '%s with suffix %s had an invalid result' % (self.name, suffix),
            'The recipe expected the result to contain the key \'failures\'.'
            ' Contents are:\n%s' % api.json.dumps(result.json.output, indent=2))

      # Most scripts do not emit 'successes'. If they start emitting
      # 'successes', then we can create a proper results dictionary.
      pass_fail_counts = {}
      for failing_test in failures:
        pass_fail_counts.setdefault(failing_test, {
            'pass_count': 0,
            'fail_count': 0
        })
        pass_fail_counts[failing_test]['fail_count'] += 1

      # It looks like the contract we have with these tests doesn't expose how
      # many tests actually ran. Just say it's the number of failures for now,
      # this should be fine for these tests.
      self.update_test_run(
          api, suffix, {
              'failures': failures,
              'valid': result.json.output['valid'] and result.retcode == 0,
              'total_tests_ran': len(failures),
              'pass_fail_counts': pass_fail_counts,
              'findit_notrun': set(),
          })

      _, failures = api.test_utils.limit_failures(failures)
      result.presentation.step_text += (
          api.test_utils.format_step_text([['failures:', failures]]))

    if result:
      # TODO(crbug.com/1227180): Specify our own custom invocation name rather
      # than parsing stderr.
      match = RDB_INVOCATION_NAME_RE.search(result.stderr)
      if match:
        inv_name = match.group(1)
        self._suffix_to_invocation_names[suffix] = inv_name

    return self._test_runs[suffix]


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


class LocalGTestTest(Test):

  def __init__(self, spec):
    super(LocalGTestTest, self).__init__(spec)
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

  @property
  def is_gtest(self):
    return True

  def compile_targets(self):
    return self.spec.override_compile_targets or [self.spec.target_name]

  def _get_runtest_kwargs(self, api):
    """Get additional keyword arguments to pass to runtest."""
    del api
    return {}

  def _get_revision(self, api, conf):
    substitutions = {
        'webrtc_got_rev':
            api.bot_update.last_returned_properties.get('got_webrtc_revision')
    }
    return {
        k: string.Template(v).safe_substitute(substitutions)
        for k, v in conf.items()
    }

  @recipe_api.composite_step
  def run(self, api, suffix):
    is_android = api.chromium.c.TARGET_PLATFORM == 'android'
    is_fuchsia = api.chromium.c.TARGET_PLATFORM == 'fuchsia'

    tests_to_retry = self._tests_to_retry(suffix)
    test_options = _test_options_for_running(self.test_options, suffix,
                                             tests_to_retry)
    args = _merge_args_and_test_options(self, self.spec.args, test_options)

    if tests_to_retry:
      args = _merge_arg(args, '--gtest_filter', ':'.join(tests_to_retry))

    resultdb = self.prep_local_rdb(api, include_artifacts=False)
    gtest_results_file = api.test_utils.gtest_results(
        add_json_log=False, leak_to=resultdb.result_file)

    step_test_data = lambda: api.test_utils.test_api.canned_gtest_output(True)

    kwargs = {
        'name': self.step_name(suffix),
        'args': args,
        'step_test_data': step_test_data,
        'resultdb': resultdb,
    }
    if is_android:
      kwargs['json_results_file'] = gtest_results_file
      kwargs['shard_timeout'] = self.spec.android_shard_timeout
    else:
      kwargs['xvfb'] = self.spec.use_xvfb
      kwargs['test_type'] = self.name
      kwargs['annotate'] = self.spec.annotate
      kwargs['test_launcher_summary_output'] = gtest_results_file
      kwargs.update(self._get_runtest_kwargs(api))

    if self.spec.perf_config:
      kwargs['perf_config'] = self._get_revision(api, self.spec.perf_config)
      kwargs['results_url'] = RESULTS_URL
      kwargs['perf_dashboard_id'] = self.spec.name
      kwargs['perf_builder_name_alias'] = self.spec.perf_builder_name_alias

    try:
      if is_android:
        api.chromium_android.run_test_suite(self.target_name, **kwargs)
      elif is_fuchsia:
        script = api.chromium.output_dir.join('bin',
                                              'run_%s' % self.target_name)
        args.extend(['--test-launcher-summary-output', gtest_results_file])
        args.extend(['--system-log-file', '${ISOLATED_OUTDIR}/system_log'])
        cmd = ['python', '-u', script] + args
        if resultdb and resultdb.enable:
          cmd = resultdb.wrap(api, cmd, step_name=self.target_name)
        api.step(self.target_name, cmd)
      else:
        api.chromium.runtest(
            self.target_name,
            revision=self.spec.revision,
            webkit_revision=self.spec.webkit_revision,
            **kwargs)
      # TODO(kbr): add functionality to generate_gtest to be able to
      # force running these local gtests via isolate from the src-side
      # JSON files. crbug.com/584469
    finally:
      step_result = api.step.active_result
      self._suffix_step_name_map[suffix] = '.'.join(step_result.name_tokens)
      if not hasattr(step_result, 'test_utils'):  # pragma: no cover
        self.update_test_run(api, suffix,
                             api.test_utils.canonical.result_format())
      # For perf tests, these runs do not return json data about
      # which tests were executed as they report to ChromePerf
      # dashboard.
      # Here we just need to be sure that all tests have passed.
      elif step_result.retcode == 0 and self.spec.perf_config:
        self.update_test_run(api, suffix,
                             api.test_utils.canonical.result_format(valid=True))
      else:
        gtest_results = step_result.test_utils.gtest_results
        self.update_test_run(api, suffix,
                             gtest_results.canonical_result_format())

      r = api.test_utils.present_gtest_failures(step_result)
      if r:
        self._gtest_results[suffix] = r

        api.test_results.upload(
            api.json.input(r.raw),
            test_type=self.name,
            chrome_revision=api.bot_update.last_returned_properties.get(
                self.spec.commit_position_property, 'refs/x@{#0}'))

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

  def render_results(self, api, results, presentation):  # pragma: no cover
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
        failure_strings.append('* ... %d more (%d total) ...' %
                               (num_failures - cls.MAX_FAILS, num_failures))
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
    return ("* %(state)s: %(total)d (%(expected)d expected, "
            "%(hi_left)s%(unexpected)d unexpected%(hi_right)s)") % dict(
                state=state,
                total=expected + unexpected,
                expected=expected,
                unexpected=unexpected,
                hi_left=hi_left,
                hi_right=hi_right)

  def upload_results(self, api, results, step_name, passed, step_suffix=None):
    # Only version 3 of results is supported by the upload server.
    if not results or results.get('version', None) != 3:
      return

    chrome_revision_cp = api.bot_update.last_returned_properties.get(
        'got_revision_cp', 'refs/x@{#0}')

    _, chrome_revision = api.commit_position.parse(str(chrome_revision_cp))
    chrome_revision = str(chrome_revision)
    api.test_results.upload(
        api.json.input(results),
        chrome_revision=chrome_revision,
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
          ('%s passed, %s failed (%s total)' %
           (len(results.passes.keys()), len(
               results.unexpected_failures.keys()), len(results.tests)),),
      ]

    else:
      if results.unexpected_flakes:
        presentation.status = api.step.WARNING
      if results.unexpected_failures or results.unexpected_skipped:
        presentation.status = (
            api.step.WARNING if self._ignore_task_failure else api.step.FAILURE)

      step_text += [
          ('Total tests: %s' % len(results.tests), [
              self._format_counts('Passed', len(results.passes.keys()),
                                  len(results.unexpected_passes.keys())),
              self._format_counts('Skipped', len(results.skipped.keys()),
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
          ]),
      ]

    # format_step_text will automatically trim these if the list is empty.
    step_text += [
        self._format_failures('Unexpected Failures',
                              results.unexpected_failures),
    ]
    step_text += [
        self._format_failures('Unexpected Flakes', results.unexpected_flakes),
    ]
    step_text += [
        self._format_failures('Unexpected Skips', results.unexpected_skipped),
    ]

    # Unknown test results mean something has probably gone wrong, mark as an
    # exception.
    if results.unknown:
      presentation.status = api.step.EXCEPTION
    step_text += [
        self._format_failures('Unknown test result', results.unknown),
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
        ['Fake results data', []],
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

  return _add_suffix(step_name, suffix)


class LayoutTestResultsHandler(JSONResultsHandler):
  """Uploads layout test results to Google storage."""

  def __init__(self):
    super(LayoutTestResultsHandler, self).__init__()
    self._layout_test_results = ''

  def upload_results(self, api, results, step_name, passed, step_suffix=None):
    # Also upload to standard JSON results handler
    JSONResultsHandler.upload_results(self, api, results, step_name, passed,
                                      step_suffix)

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
    # TODO(phajdan.jr): Pass gs_acl as a parameter, not build property.
    if api.properties.get('gs_acl'):
      archive_layout_test_args.extend(['--gs-acl', api.properties['gs_acl']])
    archive_result = api.build.python(archive_step_name,
                                      archive_layout_test_results,
                                      archive_layout_test_args)

    # TODO(tansell): Move this to render_results function
    sanitized_buildername = re.sub('[ .()]', '_', buildername)
    base = ("https://test-results.appspot.com/data/layout_results/%s/%s" %
            (sanitized_buildername, buildnumber))
    base += '/' + urllib.quote(step_name)

    # This keeps track of the link to build summary section for ci and cq.
    if not 'without patch' in step_suffix:
      self._layout_test_results = base + '/layout-test-results/results.html'
    archive_result.presentation.links['layout_test_results'] = (
        base + '/layout-test-results/results.html')
    archive_result.presentation.links['(zip)'] = (
        base + '/layout-test-results.zip')

  @property
  def layout_results_url(self):
    return self._layout_test_results


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

  def without_merge(self):
    return attr.evolve(self, merge=None)

  @property
  def name(self):
    if self.extra_suffix:
      return '%s %s' % (self._name, self.extra_suffix)
    else:
      return self._name

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

  def __init__(self, spec):
    super(SwarmingTest, self).__init__(spec)

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

  # TODO(https://crbug.com/chrome-operations/49):
  # remove this after isolate shutdown.
  def _get_isolated_or_cas_input_root(self, task_input):
    """
    This checks format of |task_input| and returns appropriate value as
    (isolated, cas_input_root).
    """
    if '/' in task_input:
      return '', task_input
    return task_input, ''

  def create_task(self, api, suffix, task_input):
    """Creates a swarming task. Must be overridden in subclasses.

    Args:
      api: Caller's API.
      suffix: Suffix added to the test name.
      task_input: Hash or digest of the isolated test to be run.

    Returns:
      A SwarmingTask object.
    """
    raise NotImplementedError()  # pragma: no cover

  def _apply_swarming_task_config(self, task, api, suffix, filter_flag,
                                  filter_delimiter):
    """Applies shared configuration for swarming tasks.
    """
    tests_to_retry = self._tests_to_retry(suffix)
    test_options = _test_options_for_running(self.test_options, suffix,
                                             tests_to_retry)
    args = _merge_args_and_test_options(self, self.spec.args, test_options)

    shards = self.spec.shards

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
    using_pgo = api.chromium_tests.m.pgo.using_pgo
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
      merge = api.chromium_tests.m.code_coverage.shard_merge(
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
        api.python.failing_step(
            'missing failed shards',
            "Retry shards with patch is being run on {}, which has no failed "
            "shards. This usually happens because of a test runner bug. The "
            "test runner reports test failures, but had exit_code 0.".format(
                self.step_name(suffix='with patch')))
    else:
      task.shard_indices = range(task.shards)

    task.build_properties = api.chromium.build_properties
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
      task_dimensions['os'] = api.chromium_swarming.prefered_os_dimension(
          api.platform.name)
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
    return self.get_task(suffix).get_invocation_names()

  def pre_run(self, api, suffix):
    """Launches the test on Swarming."""
    assert suffix not in self._tasks, ('Test %s was already triggered' %
                                       self.step_name(suffix))

    task_input = api.isolate.isolated_tests.get(self.isolate_target)
    if not task_input:
      return api.python.infra_failing_step(
          '[error] %s' % self.step_name(suffix),
          '*.isolated file for target %s is missing' % self.isolate_target)

    # Create task.
    self._tasks[suffix] = self.create_task(api, suffix, task_input)

    api.chromium_swarming.trigger_task(
        self._tasks[suffix], resultdb=self.resultdb)

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

  def __init__(self, spec):
    super(SwarmingGTestTest, self).__init__(spec)
    self._gtest_results = {}

  @Test.test_options.setter
  def test_options(self, value):
    self._test_options = value

  @property
  def is_gtest(self):
    return True

  def compile_targets(self):
    return self.spec.override_compile_targets or [self.spec.target_name]

  def create_task(self, api, suffix, task_input):
    isolated, cas_input_root = self._get_isolated_or_cas_input_root(task_input)
    task = api.chromium_swarming.gtest_task(
        raw_cmd=self._raw_cmd,
        relative_cwd=self.relative_cwd,
        isolated=isolated,
        cas_input_root=cas_input_root)
    self._apply_swarming_task_config(task, api, suffix, '--gtest_filter', ':')
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


def _get_results_handler(results_handler_name, default_handler):
  return {
      'default': lambda: default_handler,
      'layout tests': LayoutTestResultsHandler,
      'fake': FakeCustomResultsHandler,
  }[results_handler_name]()


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

  @cached_property
  def results_handler(self):
    """The handler for proessing tests results."""
    return _get_results_handler(self.results_handler_name, JSONResultsHandler())


class LocalIsolatedScriptTest(Test):

  def __init__(self, spec):
    super(LocalIsolatedScriptTest, self).__init__(spec)
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
  def uses_isolate(self):
    return True

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
  def run(self, api, suffix):
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

    temp = api.path.mkstemp()
    json_results_file = api.json.output(leak_to=temp)
    args.extend(['--isolated-script-test-output', json_results_file])

    step_test_data = lambda: api.json.test_api.output({
        'valid': True,
        'failures': []
    })

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
          'stdout': api.raw_io.output(),
      })

    resultdb = self.prep_local_rdb(api, temp=temp)
    if resultdb:
      kwargs['resultdb'] = resultdb

    try:
      api.isolate.run_isolated(
          self.name,
          api.isolate.isolated_tests[self.target_name],
          args,
          pre_args=pre_args,
          step_test_data=step_test_data,
          **kwargs)
    finally:
      # TODO(kbr, nedn): the logic of processing the output here is very similar
      # to that of SwarmingIsolatedScriptTest. They probably should be shared
      # between the two.
      step_result = api.step.active_result
      self._suffix_step_name_map[suffix] = '.'.join(step_result.name_tokens)
      results = step_result.json.output
      presentation = step_result.presentation

      test_results = api.test_utils.create_results_from_json(results)
      self.spec.results_handler.render_results(api, test_results, presentation)

      self.update_test_run(
          api, suffix, self.spec.results_handler.validate_results(api, results))

      if (api.step.active_result.retcode == 0 and
          not self._test_runs[suffix]['valid']):
        # This failure won't be caught automatically. Need to manually
        # raise it as a step failure.
        raise api.step.StepFailure(api.test_utils.INVALID_RESULTS_MAGIC)

    return self._test_runs[suffix]


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

  @cached_property
  def results_handler(self):
    """The handler for proessing tests results."""
    return _get_results_handler(self.results_handler_name,
                                JSONResultsHandler(self.ignore_task_failure))


class SwarmingIsolatedScriptTest(SwarmingTest):

  def __init__(self, spec):
    super(SwarmingIsolatedScriptTest, self).__init__(spec)
    self._isolated_script_results = None

  def compile_targets(self):
    return self.spec.override_compile_targets or [self.target_name]

  @property
  def uses_isolate(self):
    return True

  @Test.test_options.setter
  def test_options(self, value):
    self._test_options = value

  def create_task(self, api, suffix, task_input):
    isolated, cas_input_root = self._get_isolated_or_cas_input_root(task_input)
    task = api.chromium_swarming.isolated_script_task(
        raw_cmd=self.raw_cmd,
        relative_cwd=self.relative_cwd,
        isolated=isolated,
        cas_input_root=cas_input_root)

    self._apply_swarming_task_config(task, api, suffix,
                                     '--isolated-script-test-filter', '::')
    return task

  def validate_task_results(self, api, step_result):
    if getattr(step_result, 'json') and getattr(step_result.json, 'output'):
      results_json = step_result.json.output
    else:
      results_json = {}

    test_run_dictionary = (
        self.spec.results_handler.validate_results(api, results_json))
    presentation = step_result.presentation

    test_results = api.test_utils.create_results_from_json(results_json)
    self.spec.results_handler.render_results(api, test_results, presentation)

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
      self.spec.results_handler.upload_results(
          api, results, '.'.join(step_result.name_tokens),
          not bool(self.deterministic_failures(suffix)), suffix)
    return step_result


@attrs()
class AndroidTestSpec(TestSpec):
  """Spec for a test that runs against Android.

  Attributes:
    * compile_targets - The compile targets to be built for the test.
  """
  # pylint: disable=abstract-method

  compile_targets = attrib(sequence[str])


class AndroidTest(Test):

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
      self.update_test_run(api, suffix,
                           api.test_utils.canonical.result_format())
      presentation_step = api.python.succeeding_step(
          'Report %s results' % self.name, '')
      gtest_results = api.test_utils.present_gtest_failures(
          step_result, presentation=presentation_step.presentation)
      if gtest_results:
        self.update_test_run(api, suffix,
                             gtest_results.canonical_result_format())

        api.test_results.upload(
            api.json.input(gtest_results.raw),
            test_type='.'.join(step_result.name_tokens),
            chrome_revision=api.bot_update.last_returned_properties.get(
                'got_revision_cp', 'refs/x@{#0}'))

    return step_result

  def compile_targets(self):
    return self.spec.compile_targets


@attrs()
class AndroidJunitTestSpec(AndroidTestSpec):
  """Create a spec for a test that runs a Junit test on Android.

  Attributes:
    * additional_args - Additional arguments passed to the test.
  """

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


class AndroidJunitTest(AndroidTest):

  @property
  def uses_local_devices(self):
    return False

  #override
  def run_tests(self, api, suffix, json_results_file):
    return api.chromium_android.run_java_unit_test_suite(
        self.name,
        target_name=self.spec.target_name,
        verbose=True,
        suffix=suffix,
        additional_args=self.spec.additional_args,
        json_results_file=json_results_file,
        step_test_data=(
            lambda: api.test_utils.test_api.canned_gtest_output(False)),
        resultdb=self.spec.resultdb)


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

  def __init__(self, spec):
    super(MockTest, self).__init__(spec)
    # We mutate the set of failures depending on the exit code of the test
    # steps, so get a mutable copy
    self._failures = list(spec.failures)

  @property
  def runs_on_swarming(self):  # pragma: no cover
    return self.spec.runs_on_swarming

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

  def pre_run(self, api, suffix):
    with self._mock_exit_codes(api):
      api.step('pre_run {}'.format(self.step_name(suffix)), None)

  @recipe_api.composite_step
  def run(self, api, suffix):
    with self._mock_exit_codes(api):
      try:
        step_result = api.step(self.step_name(suffix), None)
      finally:
        result = api.step.active_result
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

  @property
  def abort_on_failure(self):
    return self.spec.abort_on_failure


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
  """

  platform = attrib(enum(['device', 'simulator']), default=None)
  config = attrib(mapping[str, ...], default={})
  task = attrib(mapping[str, ...], default={})
  upload_test_results = attrib(bool, default=False)
  result_callback = attrib(callable_, default=None)

  @classmethod
  def create(  # pylint: disable=arguments-differ
      cls, swarming_service_account, platform, config, task,
      upload_test_results, result_callback):
    """Create a SwarmingIosTestSpec.

    A number of attributes in the returned spec are either extracted
    from `task` or `config` or are based on the value of `platform`
    and/or values in 'task' and/or 'config'.

    Arguments:
      * swarming_service_account - The service account to run the test's
        swarming tasks as.
      * platform - The platform of the iOS target.
      * config - A dictionary detailing the build config.
      * task - A dictionary detailing the task config.
      * upload_test_results - Whether or not test results should be
        uploaded.
      * result_callback - A callback to run whenever a task finishes.
    """
    return super(SwarmingIosTestSpec, cls).create(
        name=task['step name'],
        service_account=swarming_service_account,
        platform=platform,
        config=config,
        task=task,
        upload_test_results=upload_test_results,
        result_callback=result_callback,
        cipd_packages=cls._get_cipd_packages(task),
        expiration=(task['test'].get('expiration_time') or
                    config.get('expiration_time')),
        hard_timeout=(task['test'].get('max runtime seconds') or
                      config.get('max runtime seconds')),
        dimensions=cls._get_dimensions(platform, config, task),
        optional_dimensions=task['test'].get('optional_dimensions'),
    )

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


class SwarmingIosTest(SwarmingTest):

  def pre_run(self, api, suffix):
    task = self.spec.task

    task_output_dir = api.path.mkdtemp(task['task_id'])
    raw_cmd = task.get('raw_cmd')
    if raw_cmd is not None:
      raw_cmd = list(raw_cmd)

    isolated, cas_input_root = self._get_isolated_or_cas_input_root(
        task['task input'])
    swarming_task = api.chromium_swarming.task(
        name=task['step name'],
        task_output_dir=task_output_dir,
        failure_as_exception=False,
        isolated=isolated,
        relative_cwd=task.get('relative_cwd'),
        cas_input_root=cas_input_root,
        raw_cmd=raw_cmd)

    self._apply_swarming_task_config(
        swarming_task, api, suffix, filter_flag=None, filter_delimiter=None)

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
    swarming_task.named_caches[named_cache] = api.ios.XCODE_APP_PATH

    if self.spec.platform == 'simulator':
      runtime_cache_name = 'runtime_ios_%s' % str(task['test']['os']).replace(
          '.', '_')
      runtime_cache_path = 'Runtime-ios-%s' % str(task['test']['os'])
      swarming_task.named_caches[runtime_cache_name] = runtime_cache_path

    swarming_task.tags.add('device_type:%s' % str(task['test']['device type']))
    swarming_task.tags.add('ios_version:%s' % str(task['test']['os']))
    swarming_task.tags.add('platform:%s' % self.spec.platform)
    swarming_task.tags.add('test:%s' % str(task['test']['app']))

    api.chromium_swarming.trigger_task(swarming_task)
    self._tasks[suffix] = swarming_task

  @recipe_api.composite_step
  def run(self, api, suffix):
    task = self.spec.task
    swarming_task = self._tasks[suffix]

    assert swarming_task, ('The task should have been triggered and have an '
                           'associated swarming task')

    step_result, has_valid_results = api.chromium_swarming.collect_task(
        swarming_task)
    self._suffix_step_name_map[suffix] = '.'.join(step_result.name_tokens)

    # Add any iOS test runner results to the display.
    shard_output_dir = swarming_task.get_task_shard_output_dirs()[0]
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
      canonical_results = api.test_utils.canonical.result_format(
          valid=has_valid_results,
          failures=failed_tests,
          total_tests_ran=test_count,
          pass_fail_counts=pass_fail_counts)
      self.update_test_run(api, suffix, canonical_results)

      step_result.presentation.logs['test_summary.json'] = api.json.dumps(
          test_summary_json, indent=2).splitlines()
      step_result.presentation.logs.update(logs)
      step_result.presentation.links.update(test_summary_json.get('links', {}))
      if test_summary_json.get('step_text'):
        step_result.presentation.step_text = '%s<br />%s' % (
            step_result.presentation.step_text, test_summary_json['step_text'])
    else:
      self.update_test_run(api, suffix,
                           api.test_utils.canonical.result_format())

    # Upload test results JSON to the flakiness dashboard.
    shard_output_dir_full_path = api.path.join(
        swarming_task.task_output_dir,
        swarming_task.get_task_shard_output_dirs()[0])
    if (api.bot_update.last_returned_properties and
        self.spec.upload_test_results):
      test_results = api.path.join(shard_output_dir_full_path,
                                   'full_results.json')
      if api.path.exists(test_results):
        api.test_results.upload(
            test_results,
            '.'.join(step_result.name_tokens),
            api.bot_update.last_returned_properties.get('got_revision_cp',
                                                        'refs/x@{#0}'),
            builder_name_suffix='%s-%s' %
            (task['test']['device type'], task['test']['os']),
            test_results_server='test-results.appspot.com',
        )

    # Upload performance data result to the perf dashboard.
    perf_results_path = api.path.join(shard_output_dir, 'Documents',
                                      'perf_result.json')
    if self.spec.result_callback:
      self.spec.result_callback(
          name=task['test']['app'], step_result=step_result)
    elif perf_results_path in step_result.raw_io.output_dir:
      data = api.json.loads(step_result.raw_io.output_dir[perf_results_path])
      data_decode = data['Perf Data']
      data_result = []
      for testcase in data_decode:
        for trace in data_decode[testcase]['value']:
          data_point = api.perf_dashboard.get_skeleton_point(
              'chrome_ios_perf/%s/%s' % (testcase, trace),
              # TODO(huangml): Use revision.
              int(api.time.time()),
              data_decode[testcase]['value'][trace])
          data_point['units'] = data_decode[testcase]['unit']
          data_result.extend([data_point])
      api.perf_dashboard.set_default_config()
      api.perf_dashboard.add_point(data_result)

    return step_result

  def validate_task_results(self, api, step_result):
    raise NotImplementedError()  # pragma: no cover

  def create_task(self, api, suffix, task_input):
    raise NotImplementedError()  # pragma: no cover

  def compile_targets(self):
    raise NotImplementedError()  # pragma: no cover


@attrs()
class SkylabTestSpec(TestSpec):
  """Spec for a suite that runs on CrOS Skylab."""
  cros_board = attrib(str)
  cros_img = attrib(str)
  tast_expr = attrib(str, default='')
  test_args = attrib(command_args, default=())
  timeout_sec = attrib(int, default=3600)
  # Enable retry for all Skylab tests by default. We see around 10% of tests
  # failed due to lab issues. Set retry into test requests, so that failed
  # tests could get rerun from OS infra side. We only bridged our CI builders
  # to Skylab now, so we do not expect a lot of failures from our artifact.
  # Revisit this when we integrate CQ to Skylab.
  retries = attrib(int, default=3)

  @property
  def test_class(self):
    return SkylabTest


class SkylabTest(Test):

  def __init__(self, spec):
    super(SkylabTest, self).__init__(spec)
    self.ctp_responses = []
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
        board=self.spec.cros_board,
        cros_img=self.spec.cros_img,
        lacros_gcs_path=self.lacros_gcs_path,
        exe_rel_path=self.exe_rel_path,
        timeout_sec=self.spec.timeout_sec,
        retries=self.spec.retries,
    ) if self.lacros_gcs_path else None

  def _raise_failed_step(self, api, suffix, step, status, failure_msg):
    step.presentation.status = status
    step.presentation.step_text = failure_msg
    self.update_test_run(api, suffix, api.test_utils.canonical.result_format())
    raise api.step.StepFailure(status)

  def tast_result_parser(self, api, result, suffix, step):
    """Return result dict.

    CTP response contains tast case result. Parse it to get the step's
    output presentation.
    """
    if not result.test_cases:
      self._raise_failed_step(api, suffix, step, api.step.FAILURE,
                              'No test cases returned.')

    pass_fail_counts = {}
    passed_cases, failed_cases = [], []
    for tc in result.test_cases:
      pass_fail_counts.setdefault(tc.name, {'pass_count': 0, 'fail_count': 0})
      if tc.verdict == 'PASSED':
        pass_fail_counts[tc.name]['pass_count'] += 1
        passed_cases.append(tc.name)
        continue
      pass_fail_counts[tc.name]['fail_count'] += 1
      failed_cases.append(tc.name)
    step_log = []
    if passed_cases:
      step_log += ['PASSED:'] + passed_cases + ['']
    if failed_cases:
      step_log += ['FAILED:'] + failed_cases
    step.logs['Test Cases'] = step_log if step_log else ['No test cases found']
    step.step_text += (
        '<br/>%s passed, %s failed (%s total)' %
        (len(passed_cases), len(failed_cases), len(result.test_cases)))
    self.update_test_run(
        api, suffix, {
            'failures': failed_cases,
            'valid': result is not None,
            'total_tests_ran': len(result.test_cases),
            'pass_fail_counts': pass_fail_counts,
            'findit_notrun': set(),
        })

  def gtest_result_parser(self, api, result, suffix, step):
    # TODO(crbug/1222806): Upload test result to Result DB from the skylab
    # test runner side. We are still discussing with OS infra team about the
    # implementation. Before that, parse the gtest result in our recipe.
    resultdb = attr.evolve(
        self.spec.resultdb,
        artifact_directory='',
        base_variant=dict(
            self.spec.resultdb.base_variant or {},
            test_suite=self.canonical_name),
        result_adapter_path=str(api.path['checkout'].join(
            'tools', 'resultdb', 'result_adapter')),
        result_file=api.path.abspath(api.path.mkstemp()))
    gtest_results_file = api.gsutil.download_url(
        '%s/autoserv_test/chromium/results/output.json' % result.log_gs_uri,
        api.test_utils.gtest_results(
            add_json_log=False, leak_to=resultdb.result_file),
        name='Download test result for %s' % self.name)
    if not gtest_results_file.test_utils.gtest_results.raw:
      return self._raise_failed_step(api, suffix, step, api.step.FAILURE,
                                     'No valid result file returned.')
    gtest_results = api.test_utils.present_gtest_failures(
        gtest_results_file, presentation=step.presentation)
    if gtest_results:
      self.update_test_run(api, suffix, gtest_results.canonical_result_format())
      api.test_results.upload(
          api.json.input(gtest_results.raw),
          test_type='.'.join(gtest_results_file.name_tokens),
          chrome_revision=api.bot_update.last_returned_properties.get(
              'got_revision_cp', 'refs/x@{#0}'))

  def present_result(self, api, resp, step, suffix, parser):
    if resp.verdict != "PASSED":
      step.presentation.status = api.step.FAILURE
    if resp.url:
      step.links['Test Run'] = resp.url
    if resp.log_url:
      step.links['Logs(stainless)'] = resp.log_url
    return parser(api, resp, suffix, step)

  @recipe_api.composite_step
  def run(self, api, suffix):
    self._suffix_step_name_map[suffix] = self.name

    with api.step.nest(self.name) as step:
      step_failure_msg = None
      if not self.lacros_gcs_path:
        step_failure_msg = (
            'Test was not scheduled because of absent lacros_gcs_path.')
      if step_failure_msg:
        return self._raise_failed_step(api, suffix, step, api.step.FAILURE,
                                       step_failure_msg)
      if not self.ctp_responses:
        return self._raise_failed_step(api, suffix, step, api.step.EXCEPTION,
                                       'Invalid test result.')

      parser = self.gtest_result_parser
      if self.is_tast_test:
        parser = self.tast_result_parser

      if len(self.ctp_responses) == 1:
        self.present_result(api, self.ctp_responses[0], step, suffix, parser)
      else:
        # Keep the logic simple and consider the test succeed if any
        # of the attempt passed. In long term, we will rely on ResultDB to
        # tell us the test result.
        if any(r.verdict == "PASSED" for r in self.ctp_responses):
          step.presentation.status = api.step.SUCCESS
        for i, r in enumerate(self.ctp_responses, 1):
          with api.step.nest('attempt: #' + str(i)) as attempt_step:
            try:
              self.present_result(api, r, attempt_step, suffix, parser)
            except api.step.StepFailure:
              pass

      return self._test_runs[suffix]

  def compile_targets(self):
    t = [self.spec.target_name, 'lacros_version_metadata']
    if self.is_tast_test:
      t.append('chrome')
    return t
