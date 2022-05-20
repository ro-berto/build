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

    The clusters may or may not have an associated bug.
    See go/src/infra/appengine/weetbix/proto/v1/clusters.proto in
    chromium/infra/infra.git for ClusterRequest and ClusterResponse protos.

    Args:
      test_suites: List of failing Test (chromium_tests/steps.py) objects

    Returns:
      List of ClusterResponses dicts
    """
    cluster_request_test_results = []
    for t in test_suites:
      rdb_results = t.get_rdb_results('with patch')
      failing_tests = rdb_results.unexpected_failing_tests
      for failing_test in failing_tests:
        failure_reasons = failing_test.failure_reasons
        for i in range(len(failure_reasons)):
          reason = failure_reasons[i]
          if reason:
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
      return []

    cluster_request = {
        'project': self.m.buildbucket.build.builder.project,
        'testResults': cluster_request_test_results,
    }
    return self._run(
        CLUSTER_STEP_NAME,
        'weetbix.v1.Clusters.Cluster',
        cluster_request,
    )['clusteredTestResults']
