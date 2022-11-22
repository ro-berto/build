# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""API for interacting with the LUCI Analysis RPCs

This API is for calling LUCI Analysis RPCs for various aggregated info about
test results. Weetbix is the previous name of LUCI Analysis.
See go/luci-analysis for more info.
"""

import re

from google.protobuf import json_format
from recipe_engine import recipe_api

from RECIPE_MODULES.build.attr_utils import attrib, attrs
from PB.go.chromium.org.luci.analysis.proto.v1.predicate import TestVerdictPredicate
from PB.go.chromium.org.luci.analysis.proto.v1.test_history import (
    QueryTestHistoryRequest, QueryTestHistoryResponse, QueryVariantsRequest,
    QueryVariantsResponse)
from PB.go.chromium.org.luci.analysis.proto.v1.test_variants import TestVariantFailureRateAnalysis
from PB.go.chromium.org.luci.analysis.proto.v1.clusters import QueryClusterFailuresResponse

CLUSTER_STEP_NAME = 'cluster failing test results with weetbix'


class WeetbixApi(recipe_api.RecipeApi):

  def _run(self, step_name, rpc_endpoint, request_input, step_test_data=None):
    args = [
        'prpc',
        'call',
        'luci-analysis.appspot.com',
        rpc_endpoint,
    ]
    result = self.m.step(
        step_name,
        args,
        stdin=self.m.json.input(request_input),
        stdout=self.m.json.output(add_json_log=True),
        step_test_data=step_test_data,
    )
    result.presentation.logs['input'] = self.m.json.dumps(
        request_input, indent=2)
    return result.stdout

  def query_failure_rate(self, test_suites):
    """Queries LUCI Analysis for failure rates

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
            'test_name': failing_test.test_name,
            'suite_name': suite.name,
        })

    with self.m.step.nest('query LUCI Analysis for failure rates'):
      failure_analysis_dicts = self._run(
          'rpc call', 'luci.analysis.v1.TestVariants.QueryFailureRate', {
              'project': 'chromium',
              'testVariants': test_variants_to_query,
          }).get('testVariants')

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
            test_name=test_info_for_zip['test_name'],
        )

        if suite_name not in suite_to_per_suite_analysis:
          suite_to_per_suite_analysis[suite_name] = (
              FailureRateAnalysisPerSuite.create(suite_name,
                                                 [indiv_failure_analysis]))
        else:
          suite_to_per_suite_analysis[suite_name].append_failure_analysis(
              indiv_failure_analysis)

    return suite_to_per_suite_analysis

  def query_test_history(self,
                         test_id,
                         sub_realm=None,
                         variant_predicate=None,
                         partition_time_range=None,
                         submitted_filter=None,
                         page_size=1000,
                         page_token=None):
    """A wrapper method to use `luci.analysis.v1.TestHistory` `Query` API.

    Args:
      test_id (str): test ID to query.
      sub_realm (str): Optional. The realm without the "<project>:" prefix.
        E.g. "try". Default all test verdicts will be returned.
      variant_predicate (luci.analysis.v1.VariantPredicate): Optional. The
        subset of test variants to request history for. Default all will be
        returned.
      partition_time_range (luci.analysis.v1.common.TimeRange): Optional. A
        range of timestamps to query the test history from. Default all will be
        returned. (At most recent 90 days as TTL).
      submitted_filter (luci.analysis.v1.common.SubmittedFilter): Optional.
        Whether test verdicts generated by code with unsubmitted changes (e.g.
        Gerrit changes) should be included in the response. Default all will be
        returned. Default all will be returned.
      page_size (int): Optional. The number of results per page in the response.
        If the number of results satisfying the given configuration exceeds this
        number, only the page_size results will be available in the response.
        Defaults to 1000.
      page_token (str): Optional. For instances in which the results span
        multiple pages, each response will contain a page token for the next
        page, which can be passed in to the next request. Defaults to None,
        which returns the first page.

    Returns:
      (list of parsed luci.analysis.v1.TestVerdict objects, next page token)
    """
    predicate = TestVerdictPredicate(
        sub_realm=sub_realm,
        variant_predicate=variant_predicate,
        submitted_filter=submitted_filter,
        partition_time_range=partition_time_range,
    )

    request = QueryTestHistoryRequest(
        project='chromium',
        test_id=test_id,
        predicate=predicate,
        page_size=page_size,
    )
    if page_token:
      request.page_token = page_token

    response_json = self._run('Test history query rpc call for %s' % test_id,
                              'luci.analysis.v1.TestHistory.Query',
                              json_format.MessageToDict(request))
    response = json_format.ParseDict(response_json, QueryTestHistoryResponse())
    return response.verdicts, response.next_page_token

  def query_variants(self,
                     test_id,
                     project='chromium',
                     sub_realm=None,
                     variant_predicate=None,
                     page_size=1000,
                     page_token=None):
    """A wrapper method to use `luci.analysis.v1.TestHistory` `QueryVariants`
    API.

    Args:

      test_id (str): test ID to query.
      project (str): Optional. The LUCI project to query the variants from.
      sub_realm (str): Optional. The realm without the "<project>:" prefix.
        E.g. "try". Default all test verdicts will be returned.
      variant_predicate (luci.analysis.v1.VariantPredicate): Optional. The
        subset of test variants to request history for. Default all will be
        returned.
      page_size (int): Optional. The number of results per page in the response.
        If the number of results satisfying the given configuration exceeds this
        number, only the page_size results will be available in the response.
        Defaults to 1000.
      page_token (str): Optional. For instances in which the results span
        multiple pages, each response will contain a page token for the next
        page, which can be passed in to the next request. Defaults to None,
        which returns the first page.

    Returns:
      (list of VariantInfo { variant_hash: str, variant: { def: dict } },
       next page token)
    """
    request = QueryVariantsRequest(
        project=project,
        test_id=test_id,
        sub_realm=sub_realm,
        variant_predicate=variant_predicate,
        page_size=page_size,
        page_token=page_token,
    )

    response_json = self._run(
        'Test history query_variants rpc call for %s' % test_id,
        'luci.analysis.v1.TestHistory.QueryVariants',
        json_format.MessageToDict(request))
    response = json_format.ParseDict(response_json, QueryVariantsResponse())
    return response.variants, response.next_page_token

  def lookup_bug(self, bug_id, system='monorail'):
    """Looks up the rule associated with a given bug.

    This is a wrapper of `luci.analysis.v1.Rules` `LookupBug` API.

    Args:
      bug_id (str): Bug Id is the bug tracking system-specific identity of the
        bug. For monorail, the scheme is {project}/{numeric_id}, for buganizer
        the scheme is {numeric_id}.
      system (str): System is the bug tracking system of the bug. This is either
        "monorail" or "buganizer". Defaults to monorail.

    Returns:
      list of rules (str), Format: projects/{project}/rules/{rule_id}
    """
    response_json = self._run(
        'Lookup Bug %s:%s' % (system, bug_id),
        'luci.analysis.v1.Rules.LookupBug', {
            'system': system,
            'id': bug_id,
        },
        step_test_data=lambda: self.m.json.test_api.output_stream({}))
    return response_json.get('rules', [])

  def rule_name_to_cluster_name(self, rule):
    """Convert the resource name for a rule to its corresponding cluster.
    Args:
      rule (str): Format: projects/{project}/rules/{rule_id}
    Returns:
      cluster (str): Format:
        projects/{project}/clusters/{cluster_algorithm}/{cluster_id}.
    """
    return re.sub(r'projects/(\w+)/rules/(\w+)',
                  'projects/\\1/clusters/rules/\\2', rule)

  def query_cluster_failures(self, cluster_name):
    """Queries examples of failures in the given cluster.

    This is a wrapper of `luci.analysis.v1.Clusters` `QueryClusterFailures` API.

    Args:
      cluster_name (str): The resource name of the cluster to retrieve.
        Format: projects/{project}/clusters/{cluster_algorithm}/{cluster_id}

    Returns:
      list of DistinctClusterFailure

      For value format, see [`DistinctClusterFailure` message]
      (https://bit.ly/DistinctClusterFailure)
    """
    assert not cluster_name.endswith('/failures'), cluster_name
    cluster_failure_name = cluster_name + '/failures'

    response_json = self._run(
        'Query Cluster Failure %s' % cluster_name,
        'luci.analysis.v1.Clusters.QueryClusterFailures', {
            'parent': cluster_failure_name,
        },
        step_test_data=(
            lambda: self.m.json.test_api.output_stream({'failures': []})))
    response = json_format.ParseDict(response_json,
                                     QueryClusterFailuresResponse())
    return response.failures


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


@attrs()
class IndividualTestFailureRateAnalysis(object):
  """Wraps a TestVariantFailureRateAnalysis instance for one individual test"""
  # Full test ID.
  # Consists of a suite prefix + the test_name
  # e.g. ninja://gpu:gpu_unittests/FeatureInfoTest.Basic/Service.0
  test_id = attrib(str)
  # Name of test
  # e.g. FeatureInfoTest.Basic/Service.0
  test_name = attrib(str)
  suite_name = attrib(str)
  variant_hash = attrib(str)
  # Ordered list (ascending by interval_age) of IntervalStats
  interval_stats = attrib(list)
  # List of VerdictExample protos as dicts
  # Examples of verdicts which had both expected and unexpected runs.
  # Limited to at most 10, ordered by recency
  run_flaky_verdict_examples = attrib(list, default=None)
  # List of RecentVerdict protos
  # Limited to 10 RecentVerdicts
  recent_verdicts = attrib(list, default=None)

  @classmethod
  def create(cls, failure_analysis, suite_name, test_name):
    interval_stats = [
        IntervalStats(
            interval_age=i.interval_age,
            total_run_expected_verdicts=i.total_run_expected_verdicts,
            total_run_flaky_verdicts=i.total_run_flaky_verdicts,
            total_run_unexpected_verdicts=i.total_run_unexpected_verdicts,
        ) for i in failure_analysis.interval_stats
    ]
    run_flaky_verdict_examples = [
        json_format.MessageToDict(ex)
        for ex in failure_analysis.run_flaky_verdict_examples
    ]
    return cls(
        test_id=failure_analysis.test_id,
        test_name=test_name,
        suite_name=suite_name,
        variant_hash=failure_analysis.variant_hash,
        interval_stats=interval_stats,
        run_flaky_verdict_examples=run_flaky_verdict_examples,
        recent_verdicts=list(failure_analysis.recent_verdicts),
    )

  def _get_flaky_verdict_count(self, num_intervals):
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

  def get_unexpected_recent_verdict_count(self):
    """Returns the total number of unexpected verdicts over the past 10 verdicts

    The list of RecentVerdicts returned from LUCI Analysis for a test_id is
    already limited to at most 10 verdicts.

    Return: int
    """
    return sum(
        [verdict.has_unexpected_runs for verdict in self.recent_verdicts])

  def get_flaky_verdict_counts(self, num_intervals_list):
    """Returns the number of flaky verdicts for each interval

    Args:
      num_intervals_list List(int): A list of the past intervals to look at for
        flaky verdicts. Example: if num_intervals is [1, 5], this will return
        one value for the number of flakes in the past day and another value for
        the number of flakes in the past 5 days.

    Return: int
    """
    return {
        num: self._get_flaky_verdict_count(num) for num in num_intervals_list
    }


@attrs()
class IntervalStats(object):
  """Wraps IntervalStats instance

  # Each interval currently represents 24 weekday hours, including weekend
  # hours, if applicable.
  # Because intervals represent 24 weekday hours, interval_age = 1 would be the
  # last 24 hours of weekday data before the time the query is made,
  # interval_age=2 would be the 24 hours of data before that, and so on.
  # For more info, see the
  # go/src/go.chromium.org/luci/analysis/proto/v1/test_variants.proto in
  # infra/infra.
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
