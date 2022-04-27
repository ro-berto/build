# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import attr
import collections
import six

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
      for test_fullname, results in six.iteritems(cur_iteration_data):
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


    for test_fullname, results in six.iteritems(self.raw_results):
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
    for test_name, results_dict in six.iteritems(self.pass_fail_counts):
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
  """Contains results of a single test suite as returned by RDB.

  This class is not expected to track tests with expected results. eg: If a
  test's expectations expect it to FAIL, and it FAILs, we do not track that
  here.
  """

  NEEDED_FIELDS = [
      'testId', 'variant', 'variantHash', 'status', 'tags', 'expected',
      'duration'
  ]

  suite_name = attrib(str)
  variant_hash = attrib(str)
  total_tests_ran = attrib(six.integer_types)
  unexpected_passing_tests = attrib(set)
  unexpected_failing_tests = attrib(set)
  # unexpected_skipped_tests should be a subset of unexpected_failing_tests.
  unexpected_skipped_tests = attrib(set)
  invalid = attrib(bool, default=False)
  test_name_to_test_id_mapping = attrib(mapping[str, str])
  # Mapping from test name to duration (in milliseconds) of an expectedly passed
  # run if available.
  test_named_to_passed_run_duration = attrib(mapping[str, int])
  individual_results = attrib(mapping[str, sequence[...]])
  # Mapping from test name to count of unexpected unpassed results of the test.
  individual_unexpected_unpassed_result_count = attrib(mapping[str, int])
  test_id_prefix = attrib(str, default='')

  @classmethod
  def create(cls,
             invocations,
             suite_name,
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
    test_id_prefix = ''
    results_by_test_id = collections.defaultdict(list)
    variant_hash = ''
    test_name_to_test_id_mapping = {}
    total_unexpected_results = 0
    for inv in invocations.values():
      total_unexpected_results += len(inv.test_results)
      for tr in inv.test_results:
        variant_def = getattr(tr.variant, 'def')
        inv_name = variant_def['test_suite']
        # A RDBPerSuiteResults instance shouldn't be created with invocations
        # from different suites.
        if inv_name and suite_name:
          assert inv_name == suite_name, "Mismatched invocations, %s vs %s" % (
              inv_name, suite_name)
        # The test's ID may not always directly match up with its name (see
        # go/chrome-test-id for context). So lookup the test's name in the tags,
        # but preserve a mapping from name to ID for easier look-up.
        test_name = tr.test_id
        for tag in tr.tags:
          if tag.key == 'test_name':
            test_name = tag.value
            # if test_name is provided, and the test id does match up
            # with its name, use this to deduce the test_id_prefix.
            if not test_id_prefix and test_name in tr.test_id:
              test_id_prefix = tr.test_id[:tr.test_id.index(test_name)]
            break

        # Don't bother keeping a name map for tests with uninteresting results.
        if not tr.expected:
          test_name_to_test_id_mapping[test_name] = tr.test_id
        variant_hash = tr.variant_hash
        results_by_test_id[test_name].append(tr)

    total_tests_ran = total_tests_ran or total_unexpected_results
    unexpected_failing_tests = set()
    unexpected_passing_tests = set()
    unexpected_skipped_tests = set()
    test_named_to_passed_run_duration = {}
    individual_results = {}
    individual_unexpected_unpassed_result_count = {}
    for test_name, test_results in results_by_test_id.items():
      for tr in test_results:
        # Just use duration of the first passed expected result with duration.
        if tr.expected and tr.status == test_result_pb2.PASS and tr.duration:
          duration = int(tr.duration.seconds * 1000 +
                         int(tr.duration.nanos / 1000000.0))
          test_named_to_passed_run_duration[test_name] = duration
      individual_results[test_name] = list(tr.status for tr in test_results)
      individual_unexpected_unpassed_result_count[test_name] = len([
          tr for tr in test_results
          if (not tr.expected and tr.status != test_result_pb2.PASS)
      ])
      if individual_unexpected_unpassed_result_count[test_name] > 0:
        exists_unexpected_failing_result = True
      # This filters out any tests that were auto-retried within the
      # invocation and finished with an expected result. eg: a test that's
      # expected to CRASH and runs with results [FAIL, CRASH]. RDB returns
      # these results, but we don't consider them interesting for the
      # purposes of recipe retry/pass/fail decisions.
      if any(tr.expected for tr in test_results):
        continue
      if all(tr.status != test_result_pb2.PASS for tr in test_results):
        unexpected_failing_tests.add(test_name)
        if all(tr.status == test_result_pb2.SKIP for tr in test_results):
          unexpected_skipped_tests.add(test_name)
      else:
        unexpected_passing_tests.add(test_name)

    # If there were no unexpected failing results, but the harness exited
    # non-zero, assume something went wrong in the test setup/init (eg: failure
    # in underlying hardware) and that the results are invalid.
    invalid = failure_on_exit and not exists_unexpected_failing_result

    return cls(suite_name, variant_hash, total_tests_ran,
               unexpected_passing_tests, unexpected_failing_tests,
               unexpected_skipped_tests, invalid, test_name_to_test_id_mapping,
               test_named_to_passed_run_duration, individual_results,
               individual_unexpected_unpassed_result_count, test_id_prefix)

  def with_failure_on_exit(self, failure_on_exit):
    """Returns a new instance with an updated failure_on_exit value.

    We may end up fetching a test's RDB results before we know its exit code.
    (e.g. We query RDB before we collect swarming tasks.)

    TODO(crbug.com/1245085): The ordering of events doesn't affect the results
    in the new Milo UI. So this functionality can be torn out when all users
    have migrated.

    Args:
      failure_on_exit: If True, indicates the test harness/runner exited with a
          non-zero exit code. If this occurs and no unexpected failures were
          reported, it indicates invalid test results.
    """
    return attr.evolve(
        self, invalid=(failure_on_exit and not self.unexpected_failing_tests))

  def to_jsonish(self):
    jsonish_repr = {
        'suite_name': self.suite_name,
        'variant_hash': self.variant_hash,
        'invalid': str(self.invalid),
        'total_tests_ran': self.total_tests_ran,
        'unexpected_passing_tests': sorted(self.unexpected_passing_tests),
        'unexpected_failing_tests': sorted(self.unexpected_failing_tests),
        'unexpected_skipped_tests': sorted(self.unexpected_skipped_tests),
        'test_name_to_test_id_mapping': self.test_name_to_test_id_mapping,
    }
    return jsonish_repr
