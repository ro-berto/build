# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api

from google.protobuf import timestamp_pb2

from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import (builds_service as
                                                       builds_service_pb2)
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2


class SkylabTestApi(recipe_test_api.RecipeTestApi):
  """Test examples for Skylab api."""

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
    for i in range(req_num):
      retry_suffix = (' (%d)' % (i + 1)) if i else ''
      steps.append(
          self.m.buildbucket.simulated_search_results(
              [
                  build_pb2.Build(
                      id=j,
                      status=s,
                      create_time=timestamp_pb2.Timestamp(seconds=1598338800 +
                                                          j))
                  for j, s in runner_builds
              ],
              step_name='%s.buildbucket.search%s' % (step_name, retry_suffix)))
    return sum(steps, self.empty_test_data())
