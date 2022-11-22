# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from google.protobuf import json_format
from google.protobuf import timestamp_pb2
from google.protobuf.message import Message

from recipe_engine import recipe_test_api


class WeetbixTestApi(recipe_test_api.RecipeTestApi):

  def construct_recent_verdicts(self, expected_count, unexpected_count):
    verdicts = []
    for i in range(expected_count):
      verdicts.append({
          'ingested_invocation_id': 'invocation_id_' + str(i),
          'hasUnexpectedRuns': False,
      })
    for i in range(unexpected_count):
      verdicts.append({
          'ingested_invocation_id': 'invocation_id_' + str(i * 10),
          'hasUnexpectedRuns': True,
      })
    return verdicts

  def construct_flaky_verdict_examples(self, example_times):
    verdict_examples = []
    if example_times:
      for example_time in example_times:
        verdict_examples.append({
            'partitionTime':
                timestamp_pb2.Timestamp(seconds=example_time).ToJsonString(),
        })
    return verdict_examples

  def generate_analysis(self,
                        test_name,
                        suite_name='failed_test',
                        expected_count=10,
                        unexpected_count=0,
                        flaky_verdict_count=None,
                        examples_times=None):
    flaky_verdicts1 = 0
    flaky_verdicts2 = 0
    if flaky_verdict_count != None:
      flaky_verdicts1 = flaky_verdict_count

    return {
        'testId':
            'ninja://{}/{}'.format(suite_name, test_name),
        'variantHash':
            'fake_variant_hash',
        'intervalStats': [
            {
                'intervalAge': 1,
                'totalRunExpectedVerdicts': 300,
                'totalRunUnexpectedVerdicts': 1,
                'totalRunFlakyVerdicts': flaky_verdicts1,
            },
            {
                'intervalAge': 2,
                'totalRunExpectedVerdicts': 300,
                'totalRunFlakyVerdicts': flaky_verdicts2,
            },
        ],
        'recentVerdicts':
            self.construct_recent_verdicts(
                expected_count=expected_count,
                unexpected_count=unexpected_count,
            ),
        'runFlakyVerdictExamples':
            self.construct_flaky_verdict_examples(examples_times)
    }

  def query_test_history(self,
                         response,
                         test_id,
                         parent_step_name=None,
                         step_iteration=1):
    """Emulates query_test_history() return value.
    Args:
      response: (luci.analysis.v1.test_history.QueryTestHistoryResponse) the
      response to simulate.
      test_id: (str) Test ID to query.
      parent_step_name: (str) The parent step name under which
        query_test_history is nested in, if any.
      step_iteration: (int) Used when the API is called multiple times for a
        same test_id.
    """
    parent_step_prefix = ''
    if parent_step_name:
      parent_step_prefix = ('%s.' % parent_step_name)
    step_suffix = ''
    if step_iteration > 1:
      step_suffix = ' (%d)' % step_iteration
    step_name = ('%sTest history query rpc call for %s%s' %
                 (parent_step_prefix, test_id, step_suffix))

    return self.step_data(
        step_name,
        self.m.json.output_stream(json_format.MessageToDict(response)))

  def query_variants(self,
                     response,
                     test_id,
                     parent_step_name=None,
                     step_iteration=1):
    """Emulates query_variants() return value.
    Args:
      response (luci.analysis.v1.test_history.QueryVariantsResponse): the
        response to simulate.
      test_id (str): Test ID to query.
      parent_step_name (str): The parent step name under which step is nested
        in, if any.
      step_iteration: (int) Used when the API is called multiple times for a
        same test_id.
    """
    parent_step_prefix = ''
    if parent_step_name:
      parent_step_prefix = ('%s.' % parent_step_name)
    step_suffix = ''
    if step_iteration > 1:
      step_suffix = ' (%d)' % step_iteration
    step_name = ('%sTest history query_variants rpc call for %s%s' %
                 (parent_step_prefix, test_id, step_suffix))

    return self.step_data(
        step_name,
        self.m.json.output_stream(json_format.MessageToDict(response)))

  def lookup_bug(self,
                 rules,
                 id,
                 system='monorail',
                 parent_step_name=None,
                 step_iteration=1):
    """Emulates lookup_bug() return value.
    Args:
      rules (list of rules): Format: projects/{project}/rules/{rule_id}
      id (str): Id is the bug tracking system-specific identity of the bug.
        For monorail, the scheme is {project}/{numeric_id}, for buganizer the
        scheme is {numeric_id}.
      system (str): System is the bug tracking system of the bug. This is either
        "monorail" or "buganizer". Defaults to monorail.
      parent_step_name (str): The parent step name under which step is nested
        in, if any.
      step_iteration: (int) Used when the API is called multiple times for a
        same test_id.
    """
    parent_step_prefix = ('%s.' % parent_step_name) if parent_step_name else ''
    step_suffix = (' (%d)' % step_iteration) if step_iteration > 1 else ''
    step_name = ('%sLookup Bug %s:%s%s' %
                 (parent_step_prefix, system, id, step_suffix))

    return self.step_data(step_name,
                          self.m.json.output_stream({'rules': rules}))

  def query_cluster_failures(self,
                             failures,
                             cluster_name,
                             parent_step_name=None,
                             step_iteration=1):
    """Emulates query_cluster_failures() return value.
    Args:
      failures (list of DistinctClusterFailure): https://bit.ly/DistinctClusterFailure
      cluster_name (str): The resource name of the cluster to retrieve.
        Format: projects/{project}/clusters/{cluster_algorithm}/{cluster_id}
      parent_step_name (str): The parent step name under which step is nested
        in, if any.
      step_iteration: (int) Used when the API is called multiple times for a
        same test_id.
    """
    parent_step_prefix = ('%s.' % parent_step_name) if parent_step_name else ''
    step_suffix = (' (%d)' % step_iteration) if step_iteration > 1 else ''
    step_name = ('%sQuery Cluster Failure %s%s' %
                 (parent_step_prefix, cluster_name, step_suffix))

    return self.step_data(
        step_name,
        self.m.json.output_stream({
            'failures': [
                json_format.MessageToDict(x) if isinstance(x, Message) else x
                for x in failures
            ]
        }))
