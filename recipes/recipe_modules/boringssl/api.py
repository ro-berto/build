# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import itertools
import six

from recipe_engine import recipe_api
from recipe_engine import util as recipe_util

from RECIPE_MODULES.build.chromium_tests import steps
from RECIPE_MODULES.recipe_engine.json.api import JsonOutputPlaceholder


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


class TestResultsOutputPlaceholder(JsonOutputPlaceholder):

  def result(self, presentation, test):
    ret = super(TestResultsOutputPlaceholder, self).result(presentation, test)
    return TestResults(ret)


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

    self.version = self.raw.get('version', 'simplified')
    tests = self.raw.get('tests', {})
    sep = self.raw.get('path_delimiter', '/')
    self.tests = convert_trie_to_flat_paths(tests, prefix=None, sep=sep)

    # TODO(dpranke): https://crbug.com/357866 - we should simplify the
    # handling of both the return code and parsing the actual results.
    self._json_results()

    assert self.valid is not None, (
        "TestResults.valid must be set to a "
        "non-None value when the constructor returns.")

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
        'TEXT',
        'AUDIO',
        'IMAGE',
        'IMAGE+TEXT',
    )

    skipping_statuses = (
        # SKIP - The test was not run.
        'SKIP',)

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
      if (results_inconsistent and any(
          result in (expected_results + list(passing_statuses))
          for result in distinct_results)):
        key += 'flakes'
      elif last_result in passing_statuses:
        key += 'passes'
      elif last_result in failing_statuses:
        key += 'failures'
      getattr(self, key)[test] = result

      # Goes through actual_results to get pass_fail_counts for each test.
      self.pass_fail_counts.setdefault(test, {'pass_count': 0, 'fail_count': 0})
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
    ret = self.raw.copy()
    ret.setdefault('tests', {}).update(self.tests)
    return ret


class BoringSslApi(recipe_api.RecipeApi):

  # Some test runners (such as run_web_tests.py and python tests) returns the
  # number of failures as the return code. They need to cap the return code at
  # 101 to avoid overflow or colliding with reserved values from the shell.
  MAX_FAILURES_EXIT_STATUS = 101

  @recipe_util.returns_placeholder
  def test_results(self, add_json_log=True):
    """A placeholder which will expand to '/tmp/file'.

    The recipe must provide the expected --json-test-results flag.

    The test_results will be an instance of the TestResults class.
    """
    return TestResultsOutputPlaceholder(self, add_json_log)
