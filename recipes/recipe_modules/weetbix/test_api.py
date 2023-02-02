# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from google.protobuf import json_format
from google.protobuf import timestamp_pb2
from google.protobuf.message import Message

from recipe_engine import recipe_test_api


class WeetbixTestApi(recipe_test_api.RecipeTestApi):

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
                 bug_id,
                 system='monorail',
                 parent_step_name=None,
                 step_iteration=1):
    """Emulates lookup_bug() return value.
    Args:
      rules (list of rules): Format: projects/{project}/rules/{rule_id}
      bug_id (str): Id is the bug tracking system-specific identity of the bug.
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
                 (parent_step_prefix, system, bug_id, step_suffix))

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
