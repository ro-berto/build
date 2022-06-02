# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""API for interacting with the Weetbix RPCs

This API is for calling Weetbix RPCs to determine whether a bug has been filed
by Weetbix for a failing test.
See go/weetbix for more info.
"""

from recipe_engine import recipe_api

from RECIPE_MODULES.build.attr_utils import attrib, attrs, mapping, sequence

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

  def get_clusters_for_failing_test_results(self, test_suites):
    """Retrieves weetbix clusters for failing tests

    The clusters returned from the RPC may or may not have an associated bug.
    See go/src/infra/appengine/weetbix/proto/v1/clusters.proto in
    chromium/infra/infra.git for ClusterRequest and ClusterResponse protos.
    Since this module is only being used by Chromium and we're only interested
    in clusters with bugs, this method will only return the clusters with a bug.

    Returns a mapping with test suite name, test name, and reason for failing
    test suites that have a filed weetbix bug.

    Args:
      test_suites: List of failing Test (chromium_tests/steps.py) objects

    Returns:
      Dict of {test_suite_name: {test_name: {reason: list(ClusterEntry)}}}
        See go/src/infra/appengine/weetbix/proto/v1/clusters.proto for info
        on how the ClusterEntry dict looks.
    """
    # Holds a ClusterRequest dict for each failed test and its failure reason
    cluster_request_test_results = []
    # Holds test info for each item in cluster_request_test_results. This is
    # later zipped with the ClusteredTestResult responses to construct
    # a more readable mapping.
    test_info_for_zip = []
    for suite in test_suites:
      rdb_results = suite.get_rdb_results('with patch')
      failing_tests = rdb_results.unexpected_failing_tests
      for failing_test in failing_tests:
        failure_reasons = failing_test.failure_reasons
        for i in range(len(failure_reasons)):
          reason = failure_reasons[i]
          if reason:
            test_info_for_zip.append({
                'suite_name': suite.name,
                'test_name': failing_test.test_name,
                'test_id': failing_test.test_id,
                'reason': reason,
            })
            cluster_request_test_results.append({
                'testId':
                    failing_test.test_id,
                'requestTag':
                    '{test_id}_reason_{i}'.format(
                        test_id=failing_test.test_id, i=i),
                'failureReason': {
                    'primaryErrorMessage': reason,
                }
            })
    if not cluster_request_test_results:
      return {}

    cluster_request = {
        'project': self.m.buildbucket.build.builder.project,
        'testResults': cluster_request_test_results,
    }

    with self.m.step.nest(CLUSTER_STEP_NAME) as nested_cluster_step:
      clustered_test_results = self._run(
          'rpc call',
          'weetbix.v1.Clusters.Cluster',
          cluster_request,
      )['clusteredTestResults']

      mapped_clusters = self._format_cluster_response(test_info_for_zip,
                                                      clustered_test_results)
      nested_cluster_step.presentation.logs['clusters'] = self.m.json.dumps(
          mapped_clusters, indent=2)
    return mapped_clusters

  def _format_cluster_response(self, test_info_for_zip, clustered_test_results):
    """
    Formats the clusters into a readable mapping.

    See go/src/infra/appengine/weetbix/proto/v1/clusters.proto for info on
    ClusteredTestResult and ClusterEntry.

    Args:
      test_info_for_zip: Ordered list of dicts containing suite_name, test_name,
        test_id, and reason. Each ith dict should corresponds to the ith item in
        clustered_test_results.
      clustered_test_results: List of ClusteredTestResult dicts returned from
        the weetbix.v1.Clusters.Cluster RPC. Each ith dict should corresponds to
        the ith item in test_info_for_zip.

    Returns:
      Dict of {test_suite_name: {test_name: {reason: list(ClusterEntry)}}}
    """
    test_info_to_clusters_map = {}
    for test_info, clusters_dict in zip(test_info_for_zip,
                                        clustered_test_results):
      suite_name = test_info['suite_name']
      test_name = test_info['test_name']
      reason = test_info['reason']

      assert test_info['test_id'] in clusters_dict['requestTag'], (
          'ClusterResponse requestTag not matching up with requested clusters')

      clusters = clusters_dict['clusters']
      clusters_to_return = [
          cluster for cluster in clusters if cluster.get('bug')
      ]

      if not clusters_to_return:
        continue

      if suite_name not in test_info_to_clusters_map:
        test_info_to_clusters_map[suite_name] = {
            test_name: {
                reason: clusters_to_return
            }
        }
      else:
        test_info_to_clusters_map[suite_name][test_name][reason] = (
            clusters_to_return)

    return test_info_to_clusters_map
