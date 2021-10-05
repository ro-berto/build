# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64
import json
import zlib

from google.protobuf import struct_pb2
from google.protobuf import json_format

from recipe_engine import recipe_test_api

from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import (builds_service as
                                                       builds_service_pb2)
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2
from PB.test_platform.steps.execution import ExecuteResponse, ExecuteResponses
from PB.test_platform.taskstate import TaskState
from PB.test_platform.common.task import TaskLogData


class SkylabTestApi(recipe_test_api.RecipeTestApi):
  """Test examples for Skylab api."""

  def gen_task_result(
      self,
      name,
      test_cases,
      verdict=TaskState.VERDICT_PASSED,
      life_cycle=TaskState.LIFE_CYCLE_COMPLETED,
  ):
    """Generate a fake Skylab test runner, aka a tast suite result."""
    t = ExecuteResponse.TaskResult(
        state=TaskState(verdict=verdict, life_cycle=life_cycle),
        name=name,
        task_url=('https://ci.chromium.org/p/chromeos/builders/test_runner/'
                  'test_runner/b8839265267168653505'),
        log_url=('https://stainless.corp.google.com/browse/'
                 'chromeos-autotest-results/swarming-471a63bc9c481010/'),
        log_data=TaskLogData(
            gs_url=('gs://chromeos-test-logs/'
                    'test-runner/prod/2021-06-02/foo')))
    for c in test_cases:
      t.test_cases.add(name=c.name, verdict=c.verdict)
    return t

  def gen_json_execution_response(self,
                                  tasks,
                                  verdict=TaskState.VERDICT_PASSED,
                                  life_cycle=TaskState.LIFE_CYCLE_PENDING):
    """Generate a CTP response, aka an autotest test result in jsonpb."""
    rep = ExecuteResponse(
        state=TaskState(verdict=verdict, life_cycle=life_cycle))
    rep.consolidated_results.add(attempts=tasks)
    return json_format.MessageToDict(rep)

  def test_with_multi_response(
      self,
      build_id,
      tag_resp,
  ):
    """Create a list of CTP build for each tagged response."""
    builds = []
    for i, t in enumerate(tag_resp):
      builds.append(
          build_pb2.Build(
              id=(build_id + i),
              status=common_pb2.SUCCESS,
              output=build_pb2.Build.Output(
                  properties=self._multi_response(t))))
    return builds

  def _multi_response(self, tag_resp):
    """Translate the tagged response into a struct_pb2 object."""
    responses_obj = json_format.Parse(
        json.dumps({"tagged_responses": tag_resp}),
        ExecuteResponses(),
        ignore_unknown_fields=True)
    comp_string = self._base64_compress_proto(responses_obj)
    overall = {"compressed_responses": comp_string}
    return json_format.Parse(json.dumps(overall), struct_pb2.Struct())

  def _base64_compress_proto(self, proto):
    """Encode proto message to a base64 string."""
    wire_format = proto.SerializeToString()
    return base64.encodebytes(zlib.compress(wire_format)).decode('ascii')

  def step_logs_to_ctp_by_tag(self, step_log):
    """Helper to convey the step_log into a dict of CTP request."""
    request = self.m.json.loads(step_log['request'])
    ctp_by_tag = {}
    for r in request['requests']:
      ctp_by_tag.update(r['scheduleBuild']['properties']['requests'])
    return ctp_by_tag

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
