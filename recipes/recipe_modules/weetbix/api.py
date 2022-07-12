# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""API for interacting with the Weetbix RPCs

This API is for calling Weetbix RPCs for various aggregated info about test
results.
See go/weetbix for more info.
"""

from google.protobuf import json_format
from recipe_engine import recipe_api

from RECIPE_MODULES.build.attr_utils import attrib, attrs, mapping, sequence
from PB.infra.appengine.weetbix.proto.v1.test_variants import TestVariantFailureRateAnalysis

PYTHON_VERSION_COMPATIBILITY = "PY3"

CLUSTER_STEP_NAME = 'cluster failing test results with weetbix'


class WeetbixApi(recipe_api.RecipeApi):

  def _run(self, step_name, rpc_endpoint, request_input):
    args = [
        'prpc',
        'call',
        'chops-weetbix.appspot.com',
        rpc_endpoint,
    ]
    result = self.m.step(
        step_name,
        args,
        stdin=self.m.json.input(request_input),
        stdout=self.m.json.output(add_json_log=True),
    )
    result.presentation.logs['input'] = self.m.json.dumps(
        request_input, indent=2)
    return result.stdout

  def query_failure_rate(self, test_suites):
    """Queries 'weetbix.v1.TestVariants.QueryFailureRate' for failing tests

    Args:
      test_suites list(Test): List of Test objects containing rdb results of
      failing tests
    Returns:
      Dict mapping suite_name (str) to a FailureRateAnalysisPerSuite object
    """
    test_variants_to_query = []
    test_info_for_zip = []
    for suite in test_suites:
      rdb_results = suite.get_rdb_results('with patch')
      failing_tests = rdb_results.unexpected_failing_tests
      for failing_test in failing_tests:
        test_variants_to_query.append({
            'testId': failing_test.test_id,
            'variantHash': rdb_results.variant_hash,
        })
        test_info_for_zip.append({
            'testId': failing_test.test_id,
            'suite_name': suite.name,
        })

    with self.m.step.nest('query weetbix for failure rates'):
      failure_analysis_dicts = self._run(
          'rpc call', 'weetbix.v1.TestVariants.QueryFailureRate', {
              'project': 'chromium',
              'testVariants': test_variants_to_query,
          }).get('test_variants')

      # Should not happen unless there's a server issue with the RPC
      if not failure_analysis_dicts:
        return {}

      failure_analysis_protos = [
          json_format.ParseDict(d, TestVariantFailureRateAnalysis())
          for d in failure_analysis_dicts
      ]

      suite_to_per_suite_analysis = {}
      assert len(test_info_for_zip) == len(failure_analysis_protos)
      for test_info_for_zip, failure_analysis in zip(test_info_for_zip,
                                                     failure_analysis_protos):
        suite_name = test_info_for_zip['suite_name']
        indiv_failure_analysis = IndividualTestFailureRateAnalysis.create(
            failure_analysis=failure_analysis,
            suite_name=suite_name,
        )

        if suite_name not in suite_to_per_suite_analysis:
          suite_to_per_suite_analysis[suite_name] = (
              FailureRateAnalysisPerSuite.create(suite_name,
                                                 [indiv_failure_analysis]))
        else:
          suite_to_per_suite_analysis[suite_name].append_failure_analysis(
              indiv_failure_analysis)

    return suite_to_per_suite_analysis


@attrs()
class FailureRateAnalysisPerSuite(object):
  """Wraps a list of TestVariantFailureRateAnalysis instances per test suite"""
  suite_name = attrib(str)
  # List of IndividualTestFailureRateAnalysis
  failure_analysis_list = attrib(list)
  # List of failing test_ids, each correlating to an
  # IndividualTestFailureRateAnalysis object in failure_analysis_list
  test_ids = attrib(set)

  @classmethod
  def create(cls, suite_name, failure_analysis_list):
    test_ids = set(analysis.test_id for analysis in failure_analysis_list)
    return cls(
        suite_name=suite_name,
        failure_analysis_list=failure_analysis_list,
        test_ids=test_ids,
    )

  def append_failure_analysis(self, failure_analysis):
    """Append an IndividualTestFailureRateAnalysis

    Will assert that there is not already a failure_analysis for the same test

    Args:
      failure_analysis: An IndividualTestFailureRateAnalysis instance to add
    """
    test_id = failure_analysis.test_id
    assert_msg = 'Already have an IndividualTestFailureRateAnalysis for {}'
    assert test_id not in self.test_ids, assert_msg.format(test_id)
    self.failure_analysis_list.append(failure_analysis)

  def get_flaky_tests(self, num_intervals, min_flake_count):
    """Returns the flaky test_ids over the past X intervals

    Args:
      num_intervals (int): The quantity of past intervals to look at.
      min_flake_count (int): The minimum flake count for an individual test to
        be considered flaky

    Return: List of str test_id
    """
    flaky_tests = []
    for analysis in self.failure_analysis_list:
      flaky_count = analysis.get_total_flaky_verdict_count(num_intervals)
      if flaky_count >= min_flake_count:
        flaky_tests.append(analysis.test_id)
    return flaky_tests


@attrs()
class IndividualTestFailureRateAnalysis(object):
  """Wraps a TestVariantFailureRateAnalysis instance for one individual test"""
  test_id = attrib(str)
  suite_name = attrib(str)
  # Ordered list (ascending by interval_age) of IntervalStats
  interval_stats = attrib(list)

  @classmethod
  def create(cls, failure_analysis, suite_name):
    interval_stats = [
        IntervalStats(
            interval_age=i.interval_age,
            total_run_expected_verdicts=i.total_run_expected_verdicts,
            total_run_flaky_verdicts=i.total_run_flaky_verdicts,
            total_run_unexpected_verdicts=i.total_run_unexpected_verdicts,
        ) for i in failure_analysis.interval_stats
    ]
    return cls(
        test_id=failure_analysis.test_id,
        suite_name=suite_name,
        interval_stats=interval_stats,
    )

  def get_total_flaky_verdict_count(self, num_intervals):
    """Returns the number of flaky verdicts over the past X intervals

    Args:
      num_intervals (int): The quantity of past intervals to look at.

    Return: int
    """
    count = 0
    for interval in self.interval_stats:
      if interval.interval_age > num_intervals:
        break
      count += interval.total_run_flaky_verdicts
    return count


@attrs()
class IntervalStats(object):
  """Wraps IntervalStats instance

  # Each interval currently represents 24 weekday hours, including weekend
  # hours, if applicable.
  # Because intervals represent 24 weekday hours, interval_age = 1 would be the
  # last 24 hours of weekday data before the time the query is made,
  # interval_age=2 would be the 24 hours of data before that, and so on.
  # For more info, see the
  # go/src/infra/appengine/weetbix/proto/v1/test_variants.proto in infra/infra.
  """
  interval_age = attrib(int)
  # The number of verdicts which had only expected runs.
  # An expected run is a run (e.g. swarming task) which has at least
  # one expected result, excluding skipped results.
  total_run_expected_verdicts = attrib(int, default=0)
  # The number of verdicts which had both expected and
  # unexpected runs.
  total_run_flaky_verdicts = attrib(int, default=0)
  # The number of verdicts which had only unexpected runs.
  # An unexpected run is a run (e.g. swarming task) which had only
  # unexpected results (and at least one unexpected result),
  # excluding skips.
  total_run_unexpected_verdicts = attrib(int, default=0)
