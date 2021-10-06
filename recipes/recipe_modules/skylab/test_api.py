# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api

from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import (builds_service as
                                                       builds_service_pb2)
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2


class SkylabTestApi(recipe_test_api.RecipeTestApi):
  """Test examples for Skylab api."""

  def gen_schedule_build_resps(self, step_name, req_num):
    """Emulates the step of schedule_suites().

    Args:
    * step_name: The step name to overwrite the return.
    * req_num: The number of buildbucket responses to mock.

    Returns:
      A step with mock response.
    """
    resp = []
    for i in xrange(req_num):
      resp.append(dict(schedule_build=build_pb2.Build(id=(800 + i))))
    return self.m.buildbucket.simulated_schedule_output(
        builds_service_pb2.BatchResponse(responses=resp),
        step_name='%s.buildbucket.schedule' % step_name)

  def wait_on_suites(self,
                     step_name,
                     req_num,
                     runner_builds=frozenset([(900, common_pb2.SUCCESS)])):
    """Emulates the step of wait_on_suites().

    Args:
    * step_name: The step name to overwrite the return.
    * req_num: The number of buildbucket responses to mock.
    * runner_builds: The mock test runner builds kicked off by CTP, in the
        form of (build id, build status).

    Returns:
      A list of steps with mock response.
    """
    steps = []
    for i in xrange(req_num):
      retry_suffix = (' (%d)' % (i + 1)) if i else ''
      steps.append(
          self.m.buildbucket.simulated_search_results(
              [build_pb2.Build(id=i, status=s) for i, s in runner_builds],
              step_name='%s.buildbucket.search%s' % (step_name, retry_suffix)))
    return sum(steps, self.empty_test_data())

  def step_logs_to_ctp_by_tag(self, step_log):
    """Helper to convert the step_log into a dict of CTP request."""
    request = self.m.json.loads(step_log['request'])
    ctp_by_tag = {}
    for r in request['requests']:
      ctp_by_tag.update(r['scheduleBuild']['properties']['requests'])
    return ctp_by_tag
