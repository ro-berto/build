# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections

def convert_trie_to_flat_paths(trie, prefix, sep):
  # Cloned from webkitpy.layout_tests.layout_package.json_results_generator
  # so that this code can stand alone.
  result = {}
  for name, data in trie.iteritems():
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

    if self.raw is None:
      self.version = 'simplified'
      self.tests = {}
      self.valid = False
      return

    self.version = self.raw.get('version', 'simplified')
    tests = self.raw.get('tests', {})
    sep = self.raw.get('path_delimiter', '/')
    self.tests = convert_trie_to_flat_paths(tests, prefix=None, sep=sep)

    # TODO(dpranke): https://crbug.com/357866 - we should simplify the handling
    # of both the return code and parsing the actual results.

    if self.version == 'simplified':
      self._simplified_json_results()
    else:
      self._json_results()
    assert self.valid is not None, ("TestResults.valid must be set to a "
        "non-None value when the constructor returns.")

  def canonical_result_format(self):
    """Returns a dictionary with results in canonical format.

    There are three keys:
      'valid': A Boolean indicating whether the test run was valid.
      'failures': An iterable of strings -- each the name of a test that
      failed.
      'pass_fail_counts': A dictionary that provides the number of passes and
      failures for each test. e.g.
        {
          'test3': { 'PASS_COUNT': 3, 'FAIL_COUNT': 2 }
        }
    """
    return {
      'valid': self.valid,
      'failures': self.unexpected_failures,
      'total_tests_ran': self.total_test_runs,
      'pass_fail_counts': self.pass_fail_counts,
    }

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
    for passing_test in self.passes.keys():
      self.pass_fail_counts.setdefault(
          passing_test, {'pass_count': 0, 'fail_count': 0})
      self.pass_fail_counts[passing_test]['pass_count'] += 1
    for failing_test in self.unexpected_failures.keys():
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
      Reference: https://chromium.googlesource.com/chromium/src/+/f481306ad989755ebe61cfed4ab2a4fa53044b29/third_party/blink/tools/blinkpy/web_tests/models/test_expectations.py

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

    for (test, result) in self.tests.iteritems():
      key = 'unexpected_' if result.get('is_unexpected') else ''
      data = result['actual']
      actual_results = data.split()
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
        # TODO(dpranke): https://crbug.com/357867 ...  Why are we assigning
        # result instead of actual_result here. Do we even need these things to
        # be hashes, or just lists?
        data = result
      elif last_result in failing_statuses:
        key += 'failures'
      elif last_result in skipping_statuses:
        key += 'skipped'
      else:
        # Unknown test state was found.
        key = 'unknown'
      getattr(self, key)[test] = data

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

    self.passes = set()
    self.failures = set()
    # Stores raw results of each test. Used to display test results in build
    # step logs.
    self.raw_results = collections.defaultdict(list)

    if not jsonish:
      self.valid = False
      return

    self.valid = True

    for cur_iteration_data in self.raw.get('per_iteration_data', []):
      for test_fullname, results in cur_iteration_data.iteritems():
        # Results is a list with one entry per test try. Last one is the final
        # result, the only we care about for the .passes and .failures
        # attributes.
        last_result = results[-1]
        if last_result['status'] == 'SUCCESS':
          self.passes.add(test_fullname)
        elif last_result['status'] != 'SKIPPED':
          self.failures.add(test_fullname)

        # The pass_fail_counts attribute takes into consideration all runs.

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
          self.raw_results[test_fullname].append(cur_result['status'])

          ascii_log = cur_result['output_snippet'].encode('ascii',
                                                          errors='replace')
          self.logs[test_fullname].extend(
              self._compress_list(ascii_log.splitlines()))

    # With multiple iterations a test could have passed in one but failed
    # in another. Remove tests that ever failed from the passing set.
    self.passes -= self.failures

  @property
  def total_tests_ran(self):
    return len(self.passes) + len(self.failures)

  def _compress_list(self, lines):
    if len(lines) > self.MAX_LOG_LINES: # pragma: no cover
      remove_from_start = self.MAX_LOG_LINES / 2
      return (lines[:remove_from_start] +
              ['<truncated>'] +
              lines[len(lines) - (self.MAX_LOG_LINES - remove_from_start):])
    return lines

  def canonical_result_format(self):
    """Returns a dictionary with results in canonical format."""
    global_tags = self.raw.get('global_tags')
    unreliable = 'UNRELIABLE_RESULTS' in global_tags if global_tags else False
    return {
      'valid': self.valid and not unreliable,
      'failures': sorted(self.failures),
      'total_tests_ran': self.total_tests_ran,
      'pass_fail_counts': self.pass_fail_counts,
    }
