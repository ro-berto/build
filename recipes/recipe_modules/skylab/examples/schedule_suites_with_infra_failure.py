# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'recipe_engine/assertions',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'skylab',
]

from google.protobuf import json_format

from RECIPE_MODULES.build.skylab import structs

from recipe_engine.post_process import StepException

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2
from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import (builds_service as
                                                       builds_service_pb2)


def RunSteps(api):
  got = api.skylab.wait_on_suites(1234, timeout_seconds=3600)
  api.assertions.assertEqual(got.status, common_pb2.INFRA_FAILURE)


def GenTests(api):

  yield api.test(
      'mocking_timeout',
      # Mock infa failure which raises a step failure. We can not use
      # api.buildbucket.simulated_collect_output because it only return
      # the failed build, instead of raising a StepFailure, which
      # api.buildbucket.collect_build() does.
      api.step_data(
          'collect skylab results.buildbucket.collect.wait',
          api.json.output(json_format.MessageToJson(build_pb2.Build(id=0))),
          retcode=1),
      api.buildbucket.simulated_get(
          build_pb2.Build(id=1234, status=common_pb2.INFRA_FAILURE),
          step_name='collect skylab results.buildbucket.get'),
      api.post_process(StepException, 'collect skylab results'),
  )
