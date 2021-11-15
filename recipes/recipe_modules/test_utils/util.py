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


def convert_trie_to_flat_paths(trie, prefix, sep):
  # Cloned from webkitpy.layout_tests.layout_package.json_results_generator
  # so that this code can stand alone.
  result = {}
  for name, data in six.iteritems(trie):
    if prefix:
      name = prefix + sep + name

    if len(data) and not "actual" in data and not "expected" in data:
      result.update(convert_trie_to_flat_paths(data, name, sep))
    else:
      result[name] = data

  return result


class TestResults(object):
  def __init__(self, jsonish):
    self.raw = jsonish
    self.interrupted = False
    self.passes = {}
    self.unexpected_passes = {}
    self.failures = {}
    self.unexpected_failures = {}
    self.flakes = {}
    self.unexpected_flakes = {}
    self.skipped = {}
    self.unexpected_skipped = {}
    self.unknown = {}
    self.pass_fail_counts = {}

    # Both simplified JSON results and blink layout test results do not support
    # the NOTRUN/UNKNOWN tags. We do not need any additional FindIt logic here.
    self.findit_notrun = set()

    if self.raw is None:
      self.version = 'simplified'
      self.tests = {}
      self.valid = False
      return

    try:
      self.version = self.raw.get('version', 'simplified')
      tests = self.raw.get('tests', {})
      sep = self.raw.get('path_delimiter', '/')
      self.tests = convert_trie_to_flat_paths(tests, prefix=None, sep=sep)

      # TODO(dpranke): https://crbug.com/357866 - we should simplify the
      # handling of both the return code and parsing the actual results.

      if self.version == 'simplified':
        self._simplified_json_results()
      else:
        self._json_results()
    except Exception:
      # On parsing failure, mark the result as invalid. This will be presented
      # to users as INVALID_TEST_RESULTS.
      self.valid = False

    assert self.valid is not None, ("TestResults.valid must be set to a "
        "non-None value when the constructor returns.")

  def canonical_result_format(self):
    """Returns a dictionary with results in canonical format."""
    unreliable = False
    if self.raw:
      global_tags = self.raw.get('global_tags', [])
      unreliable = 'UNRELIABLE_RESULTS' in global_tags

    # If the results are interrupted or unreliable, then they're not valid
    valid = self.valid
    if self.interrupted or unreliable:
      valid = False

    return canonical.result_format(
        valid=valid,
        failures=list(self.unexpected_failures),
        total_tests_ran=self.total_test_runs,
        pass_fail_counts=self.pass_fail_counts,
        findit_notrun=self.findit_notrun)

  @property
  def total_test_runs(self):
    # Number of tests actually run, hence exclude skipped tests.
    return sum([
        len(self.passes), len(self.unexpected_passes),
        len(self.failures), len(self.unexpected_failures),
        len(self.flakes), len(self.unexpected_flakes),
    ])

  # TODO(tansell): https://crbug.com/704066 - Kill simplified JSON format.
  def _simplified_json_results(self):
    self.valid = self.raw.get('valid', False)
    self.passes = {x: {} for x in self.raw.get('successes', [])}
    self.unexpected_failures = {x: {} for x in self.raw.get('failures', [])}
    for passing_test in self.passes:
      self.pass_fail_counts.setdefault(
          passing_test, {'pass_count': 0, 'fail_count': 0})
      self.pass_fail_counts[passing_test]['pass_count'] += 1
    for failing_test in self.unexpected_failures:
      self.pass_fail_counts.setdefault(
          failing_test, {'pass_count': 0, 'fail_count': 0})
      self.pass_fail_counts[failing_test]['fail_count'] += 1
    self.tests = {}
    self.tests.update(self.passes)
    self.tests.update(self.unexpected_failures)

  def _json_results(self):
    self.valid = self.raw.get('version', 0) == 3
    self.interrupted = self.raw.get('interrupted', False)

    # Test result types are described on the follow page.
    # https://www.chromium.org/developers/the-json-test-results-format#TOC-Test-result-types

    passing_statuses = (
        # PASS - The test ran as expected.
        'PASS',
        # SLOW - Layout test specific. The test is expected to take longer than
        # normal to run.
        'SLOW',
        # WONTFIX - **Undocumented** - Test is failing and won't be fixed?
        'WONTFIX',
    )

    failing_statuses = (
        # FAIL - The test did not run as expected.
        'FAIL',
        # CRASH - The test runner crashed during the test.
        'CRASH',
        # TIMEOUT - The test hung (did not complete) and was aborted.
        'TIMEOUT',
        # MISSING - Layout test specific. The test completed but we could not
        # find an expected baseline to compare against.
        'MISSING',
        # LEAK - Layout test specific. Memory leaks were detected during the
        # test execution.
        'LEAK',
        # TEXT, AUDIO, IMAGE, IMAGE+TEXT - Layout test specific, deprecated.
        # The test is expected to produce a failure for only some parts.
        # Normally you will see "FAIL" instead.
        'TEXT', 'AUDIO', 'IMAGE', 'IMAGE+TEXT',
    )

    skipping_statuses = (
        # SKIP - The test was not run.
        'SKIP',
    )

    def result_is_regression(actual_result, expected_results):
      """Returns whether a failed result is regression.

      The logic here should match the calculation of is_regression: cannot use
      is_regression directly though because is_regression only reflects the
      *last* result.
      Reference:
        https://chromium.googlesource.com/chromium/src/+/f481306ad989755ebe61cfed4ab2a4fa53044b29/third_party/blink/tools/blinkpy/web_tests/models/test_expectations.py

      Args:
        actual_result: actual result of a test execution.
        expected_results: set of results listed in test_expectations.
      """
      local_expected = set(expected_results)
      if not local_expected:
        local_expected = {'PASS'}

      if actual_result in ('TEXT', 'AUDIO', 'IMAGE', 'IMAGE+TEXT'
                           ) and 'FAIL' in local_expected:
        return True
      return actual_result in local_expected

    for (test, result) in six.iteritems(self.tests):
      key = 'unexpected_' if result.get('is_unexpected') else ''
      actual_results = result['actual'].split()
      last_result = actual_results[-1]
      expected_results = result['expected'].split()

      # Checks len(set(actial_results)) to accommodate repeat case: if repeat,
      # test will run n iterations as told and not stop when test passes.
      distinct_results = set(actual_results)
      results_inconsistent = len(distinct_results) > 1
      if (results_inconsistent and
          any(result in (expected_results + list(passing_statuses))
          for result in distinct_results)):
        key += 'flakes'
      elif last_result in passing_statuses:
        key += 'passes'
      elif last_result in failing_statuses:
        key += 'failures'
      elif last_result in skipping_statuses:
        key += 'skipped'
      else:
        # Unknown test state was found.
        key = 'unknown'
      getattr(self, key)[test] = result

      # Goes through actual_results to get pass_fail_counts for each test.
      self.pass_fail_counts.setdefault(
          test, {'pass_count': 0, 'fail_count': 0})
      for actual_result in actual_results:
        if (actual_result in failing_statuses and
            not result_is_regression(actual_result, expected_results)):
          # Only considers a regression (unexpected failure) as a failure.
          self.pass_fail_counts[test]['fail_count'] += 1
        elif actual_result not in skipping_statuses:
          # Considers passing runs (expected or unexpected) and expected failing
          # runs as pass.
          # Skipped tests are not counted.
          self.pass_fail_counts[test]['pass_count'] += 1
        else:
          self.pass_fail_counts[test]['fail_count'] = 0


  def add_result(self, name, expected, actual=None):
    """Adds a test result to a 'json test results' compatible object.
    Args:
      name - A full test name delimited by '/'. ex. 'some/category/test.html'
      expected - The string value for the 'expected' result of this test.
      actual (optional) - If not None, this is the actual result of the test.
                          Otherwise this will be set equal to expected.

    The test will also get an 'is_unexpected' key if actual != expected.
    """
    actual = actual or expected
    entry = self.tests
    for token in name.split('/'):
      entry = entry.setdefault(token, {})
    entry['expected'] = expected
    entry['actual'] = actual
    if expected != actual:  # pragma: no cover
      entry['is_unexpected'] = True
      # TODO(dpranke): crbug.com/357866 - this test logic is overly-simplified
      # and is counting unexpected passes and flakes as regressions when it
      # shouldn't be.
      self.raw['num_regressions'] += 1

  def as_jsonish(self):
    if self.raw is None:
      return None
    ret = self.raw.copy()
    ret.setdefault('tests', {}).update(self.tests)
    return ret


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
      'testId', 'variant', 'variantHash', 'status', 'tags', 'expected'
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
  individual_results = attrib(mapping[str, sequence[...]])

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
    individual_results = {}
    for test_name, test_results in results_by_test_id.items():
      individual_results[test_name] = list(tr.status for tr in test_results)
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

    # If there were no test failures, but the harness exited non-zero, assume
    # something went wrong in the test setup/init (eg: failure in underlying
    # hardware) and that the results are invalid.
    invalid = failure_on_exit and not unexpected_failing_tests

    return cls(suite_name, variant_hash, total_tests_ran,
               unexpected_passing_tests, unexpected_failing_tests,
               unexpected_skipped_tests, invalid, test_name_to_test_id_mapping,
               individual_results)

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
