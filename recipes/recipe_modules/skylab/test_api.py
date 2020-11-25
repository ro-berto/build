# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from google.protobuf import struct_pb2
from google.protobuf import json_format

from recipe_engine import recipe_test_api

from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2
from PB.test_platform.steps.execution import ExecuteResponse, ExecuteResponses
from PB.test_platform.taskstate import TaskState


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
        task_url=("https://chromeos-swarming.appspot.com/task?id="
                  "471a63bc9c481010"),
        log_url=("https://stainless.corp.google.com/browse/"
                 "chromeos-autotest-results/swarming-471a63bc9c481010/"),
    )
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
    """Create a CTP build wrapping multiple CTP responses."""
    return build_pb2.Build(
        id=build_id,
        status=common_pb2.SUCCESS,
        output=build_pb2.Build.Output(
            properties=self._multi_response(tag_resp)))

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
    return wire_format.encode('zlib_codec').encode('base64_codec')
