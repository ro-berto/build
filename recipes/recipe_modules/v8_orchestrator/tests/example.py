# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from PB.recipe_engine import result as result_pb2
from PB.recipe_modules.recipe_engine.led import properties as led_properties_pb
from recipe_engine.post_process import (
    DropExpectation, Filter, ResultReason, StatusException,
    StatusFailure, StatusSuccess)
from recipe_engine.recipe_api import Property
from google.protobuf import json_format
from google.protobuf import struct_pb2
DEPS = [
    'recipe_engine/buildbucket',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/step',
    'v8_orchestrator',
]

PROPERTIES = {
    'revision': Property(kind=str, default=None),
}


def RunSteps(api, revision):
  handler = api.v8_orchestrator.create_compilator_handler()
  build = handler.trigger_compilator('some-builder', revision=revision)
  sub_build = handler.launch_compilator_watcher(build)
  return result_pb2.RawResult(
        status=sub_build.status, summary_markdown=sub_build.summary_markdown)


def GenTests(api):
  def subbuild_data(summary='All good!', status=common_pb.SUCCESS):
    sub_build = build_pb2.Build(
        id=54321,
        status=status,
        summary_markdown=summary,
        output=dict(
            properties=json_format.Parse(
                api.json.dumps({'prop': 'value'}), struct_pb2.Struct())))
    return api.step_data('compilator steps', api.step.sub_build(sub_build))

  yield api.test(
      'basic try',
      api.buildbucket.try_build(builder='v8_foobar'),
      subbuild_data(),
  )

  yield api.test(
      'basic ci',
      api.buildbucket.ci_build(builder='V8 Foobar'),
      api.properties(revision="abcd"),
      subbuild_data(),
      api.post_process(StatusSuccess),
      api.post_process(Filter().include('trigger compilator')),
  )

  yield api.test(
      'compiler failure',
      api.buildbucket.ci_build(builder='V8 Foobar'),
      api.properties(revision="abcd"),
      subbuild_data('Compile failed', common_pb.FAILURE),
      api.post_process(StatusFailure),
      api.post_process(ResultReason, 'Compile failed'),
      api.post_process(DropExpectation),
  )

  yield api.test(
      'no subbuild',
      api.buildbucket.ci_build(builder='V8 Foobar'),
      api.properties(revision="abcd"),
      api.post_process(StatusException),
      api.post_process(ResultReason, 'sub_build missing from step'),
      api.post_process(DropExpectation),
  )

  led_properties = {
      '$recipe_engine/led':
          led_properties_pb.InputProperties(
              led_run_id='fake-run-id',
          ),
  }

  build_proto_json = {
    'status': common_pb.SUCCESS,
    'summary': '',
    'output': {
      'properties': {'other_prop': 'other value'},
    },
  }

  yield api.test(
      'led try',
      api.buildbucket.try_build(builder='v8_foobar'),
      api.properties(**led_properties),
      api.step_data(
          'read build.proto.json',
          api.file.read_json(json_content=build_proto_json)),
      api.post_process(StatusSuccess),
      api.post_process(Filter().include('trigger compilator.led launch')),
  )

  yield api.test(
      'led ci',
      api.buildbucket.ci_build(builder='V8 Foobar'),
      api.properties(revision="abcd"),
      api.properties(**led_properties),
      api.step_data(
          'read build.proto.json',
          api.file.read_json(json_content=build_proto_json)),
      api.post_process(StatusSuccess),
      api.post_process(Filter().include('trigger compilator.led launch')),
  )