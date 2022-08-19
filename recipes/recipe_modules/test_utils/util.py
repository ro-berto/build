# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import attr
import collections

from . import canonical

from PB.go.chromium.org.luci.resultdb.proto.v1 import (test_result as
                                                       test_result_pb2)

from RECIPE_MODULES.build.attr_utils import attrib, attrs, mapping, sequence


class GTestResults(object):

  MAX_LOG_LINES = 5000

  def __init__(self, jsonish=None):
    self.logs = {}
    self.raw = jsonish or {}
    self.pass_fail_counts = {}

    # In the short term, the FindIt logic for ignoring NOTRUN/UNKNOWN tests
    # [treating them as equivalent to a passing test] is implemented in the
    # chromium tests recipe.
    # https://bugs.chromium.org/p/chromium/issues/detail?id=872042#c32

    # A set of tests which were never run [every test result was NOTRUN or
    # UNKNOWN or SKIPPED].
    self.findit_notrun = set()

    # Stores raw results of each test. Used to display test results in build
    # step logs.
    self.raw_results = collections.defaultdict(list)

    if not jsonish:
      self.valid = False
      return

    self.valid = True

    for cur_iteration_data in self.raw.get('per_iteration_data', []):
      for test_fullname, results in cur_iteration_data.items():
        # TODO (robertocn): Consider a failure in any iteration a failure of
        # the whole test, but allow for an override that makes a test pass if
        # it passes at least once.
        self.pass_fail_counts.setdefault(
            test_fullname, {'pass_count': 0, 'fail_count': 0})
        self.logs.setdefault(test_fullname, [])
        for cur_result in results:
          if cur_result['status'] == 'SUCCESS':
            self.pass_fail_counts[test_fullname]['pass_count'] += 1
          elif cur_result['status'] != 'SKIPPED':
            self.pass_fail_counts[test_fullname]['fail_count'] += 1
          else:
            self.pass_fail_counts[test_fullname]['fail_count'] = 0
          self.raw_results[test_fullname].append(cur_result['status'])

          ascii_log = cur_result['output_snippet'].encode('ascii',
                                                          errors='replace')
          self.logs[test_fullname].extend(
              self._compress_list(ascii_log.splitlines()))


    for test_fullname, results in self.raw_results.items():
      # These strings are defined by base/test/launcher/test_result.cc.
      # https://cs.chromium.org/chromium/src/base/test/launcher/test_result.cc
      unique_results = set(results)
      if unique_results.issubset(set(['UNKNOWN', 'NOTRUN', 'SKIPPED'])):
        self.findit_notrun.add(test_fullname)

  @property
  def total_tests_ran(self):
    return len(self.pass_fail_counts)

  @property
  def unique_failures(self):
    """Returns the set of tests that failed at least once."""
    failures = set()
    for test_name, results_dict in self.pass_fail_counts.items():
      if results_dict['fail_count'] >= 1:
        failures.add(test_name)
    return failures

  @property
  def deterministic_failures(self):
    return canonical.deterministic_failures(self.canonical_result_format())

  def _compress_list(self, lines):
    if len(lines) > self.MAX_LOG_LINES:
      remove_from_start = self.MAX_LOG_LINES // 2
      return (lines[:remove_from_start] +
              ['<truncated>'] +
              lines[len(lines) - (self.MAX_LOG_LINES - remove_from_start):])
    return lines

  def canonical_result_format(self):
    """Returns a dictionary with results in canonical format."""
    global_tags = self.raw.get('global_tags', [])
    unreliable = 'UNRELIABLE_RESULTS' in global_tags
    interrupted = 'CAUGHT_TERMINATION_SIGNAL' in global_tags
    return canonical.result_format(
        valid=self.valid and not unreliable and not interrupted,
        failures=sorted(self.unique_failures),
        total_tests_ran=self.total_tests_ran,
        pass_fail_counts=self.pass_fail_counts,
        findit_notrun=self.findit_notrun)


@attrs()
class RDBResults(object):
  """Like TestResults above, but used to handle results as returned by RDB.

  Wraps a collection of RDBPerSuiteResults instances.
  """

  all_suites = attrib(list)
  unexpected_failing_suites = attrib(list)

  @classmethod
  def create(cls, results):
    all_suites = []
    unexpected_failing_suites = []

    for res in results:
      assert isinstance(res, RDBPerSuiteResults)
      all_suites.append(res)
      if res.unexpected_failing_tests or res.invalid:
        unexpected_failing_suites.append(res)

    return cls(all_suites, unexpected_failing_suites)

  def to_jsonish(self):
    jsonish_repr = {
        'unexpected_failing_suites': [
            s.suite_name for s in self.unexpected_failing_suites
        ],
        'all_suites': [s.to_jsonish() for s in self.all_suites],
    }
    return jsonish_repr


@attrs()
class RDBPerSuiteResults(object):
  """Contains results of a single test suite as returned by RDB."""

  NEEDED_FIELDS = [
      'testId',
      'variant',
      'variantHash',
      'status',
      'tags',
      'expected',
      'duration',
      'failureReason',
  ]

  suite_name = attrib(str)
  variant_hash = attrib(str)
  total_tests_ran = attrib(int)
  unexpected_passing_tests = attrib(set)
  unexpected_failing_tests = attrib(set)
  # unexpected_skipped_tests should be a subset of unexpected_failing_tests.
  unexpected_skipped_tests = attrib(set)
  invalid = attrib(bool, default=False)
  # A mapping from test name str to its |RDBPerIndividualTestResults| object
  # for tests without any expected results.
  individual_unexpected_test_by_test_name = attrib(mapping[str, ...])
  # A list of all |RDBPerIndividualTestResults| objects within this class.
  all_tests = attrib(sequence[...])
  # |test_id_prefix| from the test specs in testing/buildbot. Empty str if it's
  # not set, or if any test IDs from invocations don't have the exact prefix
  # as input.
  test_id_prefix = attrib(str, default='')
  # This is a field used in |with_failure_on_exit| method.
  # TODO(crbug.com/1245085): Remove this when |with_failure_on_exit| is removed.
  exists_unexpected_failing_result = attrib(bool, default=False)

  @classmethod
  def create(cls,
             invocations,
             suite_name,
             test_id_prefix,
             total_tests_ran,
             failure_on_exit=False):
    """
    Args:
      invocations, dict of {invocation_id: api.resultdb.Invocation} as
          returned by resultdb recipe_module's query().
      failure_on_exit: If True, indicates the test harness/runner exited with a
          non-zero exit code. If this occurs and no unexpected failures were
          reported, it indicates invalid test results.
    """
    exists_unexpected_failing_result = False
    results_by_test_id = collections.defaultdict(list)
    variant_hash = ''
    total_results = 0
    test_id_prefix = test_id_prefix or ''

    for inv in invocations.values():
      total_results += len(inv.test_results)
      for tr in inv.test_results:
        variant_def = getattr(tr.variant, 'def')
        inv_name = variant_def['test_suite']
        # A RDBPerSuiteResults instance shouldn't be created with invocations
        # from different suites.
        if inv_name and suite_name:
          assert inv_name == suite_name, "Mismatched invocations, %s vs %s" % (
              inv_name, suite_name)
        variant_hash = tr.variant_hash
        results_by_test_id[tr.test_id].append(tr)
        # Use empty test_id_prefix if there is conflict.
        if not tr.test_id.startswith(test_id_prefix):
          test_id_prefix = ''

    total_tests_ran = total_tests_ran or total_results
    unexpected_failing_tests = set()
    unexpected_passing_tests = set()
    unexpected_skipped_tests = set()
    individual_unexpected_test_by_test_name = {}
    all_tests = []
    for test_id, test_results in results_by_test_id.items():
      individual_test = RDBPerIndividualTestResults.create(
          test_id, test_results, test_id_prefix)
      if individual_test.unexpected_unpassed_count() > 0:
        exists_unexpected_failing_result = True
      all_tests.append(individual_test)
      # This filters out any tests that were auto-retried within the
      # invocation and finished with an expected result. eg: a test that's
      # expected to CRASH and runs with results [FAIL, CRASH]. RDB returns
      # these results, but we don't consider them interesting for the
      # purposes of recipe retry/pass/fail decisions.
      if any(tr.expected for tr in test_results):
        continue
      individual_unexpected_test_by_test_name[
          individual_test.test_name] = individual_test
      if all(tr.status != test_result_pb2.PASS for tr in test_results):
        unexpected_failing_tests.add(individual_test)
        if all(tr.status == test_result_pb2.SKIP for tr in test_results):
          unexpected_skipped_tests.add(individual_test)
      else:
        unexpected_passing_tests.add(individual_test)

    # If there were no unexpected failing results, but the harness exited
    # non-zero, assume something went wrong in the test setup/init (eg: failure
    # in underlying hardware) and that the results are invalid.
    invalid = failure_on_exit and not exists_unexpected_failing_result

    return cls(
        suite_name=suite_name,
        variant_hash=variant_hash,
        total_tests_ran=total_tests_ran,
        unexpected_passing_tests=unexpected_passing_tests,
        unexpected_failing_tests=unexpected_failing_tests,
        unexpected_skipped_tests=unexpected_skipped_tests,
        invalid=invalid,
        individual_unexpected_test_by_test_name=(
            individual_unexpected_test_by_test_name),
        all_tests=all_tests,
        test_id_prefix=test_id_prefix,
        exists_unexpected_failing_result=exists_unexpected_failing_result)

  def with_failure_on_exit(self, failure_on_exit):
    """Returns a new instance with an updated |invalid| value.

    We may end up fetching a test's RDB results before we know its exit code.
    (e.g. We query RDB before we collect swarming tasks.)

    TODO(crbug.com/1245085): The ordering of events doesn't affect the results
    in the new Milo UI. So this functionality can be torn out when all users
    have migrated.

    Args:
      failure_on_exit: If True, indicates the test harness/runner exited with a
          non-zero exit code. If this occurs and no unexpected results were
          reported, it indicates invalid test results.
    """
    return attr.evolve(
        self,
        invalid=(failure_on_exit and not self.exists_unexpected_failing_result))

  def to_jsonish(self):

    def _names_of_tests(tests):
      return sorted([t.test_name for t in tests])

    jsonish_repr = {
        'suite_name':
            self.suite_name,
        'test_id_prefix':
            self.test_id_prefix,
        'variant_hash':
            self.variant_hash,
        'invalid':
            str(self.invalid),
        'total_tests_ran':
            self.total_tests_ran,
        'unexpected_passing_tests':
            _names_of_tests(self.unexpected_passing_tests),
        'unexpected_failing_tests':
            _names_of_tests(self.unexpected_failing_tests),
        'unexpected_skipped_tests':
            _names_of_tests(self.unexpected_skipped_tests),
        'all_tests':
            _names_of_tests(self.all_tests),
    }
    return jsonish_repr


@attrs()
class RDBPerIndividualTestResults(object):
  """Contains result info of an individual test as returned by RDB.

  "individual test" is uniquely identified by test id. For each individual test
  within a test_suite, there could be multiple test results from being retried,
  or repeated within shards of the suite. These result info are stored in
  |statuses|, |expectednesses|, etc.
  """
  # Read from any result's test_name tag. If not exist, use the part of test_id
  # after test_id_prefix.
  # e.g. Service/FeatureInfoTest.Basic/0
  test_name = attrib(str)
  # Full test ID.
  # e.g. ninja://gpu:gpu_unittests/FeatureInfoTest.Basic/Service.0
  test_id = attrib(str)
  # A duration of any passed run.
  duration_milliseconds = attrib(int, default=None)
  # |statuses| and |expectednesses| are outcomes of single results.
  # Values at each index are for the same test run.
  statuses = attrib(sequence[...])
  expectednesses = attrib(sequence[bool])
  # Reasons of all results corresponding to |statuses|. Empty str if the
  # raw RDB result doesn't have this stored.
  failure_reasons = attrib(sequence[str])

  @classmethod
  def create(cls, test_id, test_results, test_id_prefix):
    """
    Args:
      test_id: The test ID of results.
      test_results: All results of the test id.
      test_id_prefix: The test ID prefix of the |RDBPerSuiteResults| where this
        result is grouped into.
    """
    duration_milliseconds = None
    test_name = None
    test_id = ''
    statuses = [tr.status for tr in test_results]
    expectednesses = [tr.expected for tr in test_results]
    failure_reasons = [
        tr.failure_reason.primary_error_message or '' for tr in test_results
    ]
    for tr in test_results:
      test_id = tr.test_id
      # Use duration of the last passed expected result with duration.
      if tr.expected and tr.status == test_result_pb2.PASS and tr.duration:
        duration_milliseconds = int(tr.duration.seconds * 1000 +
                                    int(tr.duration.nanos / 1000000.0))
      # Use test name tag of the last result with the tag.
      for tag in tr.tags:
        if tag.key == 'test_name':
          test_name = tag.value

    assert test_id.startswith(test_id_prefix)
    # If not found in tags, use the part after test id prefix in test ID.
    if not test_name:
      test_name = test_id[len(test_id_prefix):]

    return cls(test_name, test_id, duration_milliseconds, statuses,
               expectednesses, failure_reasons)

  def total_test_count(self):
    return len(self.statuses)

  def unexpected_unpassed_count(self):
    return sum([(status != test_result_pb2.PASS and not expected)
                for status, expected in zip(self.statuses, self.expectednesses)
               ])
