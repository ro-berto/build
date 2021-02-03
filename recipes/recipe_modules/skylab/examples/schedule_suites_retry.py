# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'skylab',
]

from RECIPE_MODULES.build.skylab import structs

from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import (builds_service as
                                                       builds_service_pb2)


def gen_skylab_req(tag):
  return structs.SkylabRequest.create(
      request_tag=tag,
      board='eve',
      tast_expr='lacros.Basic',
      cros_img='eve-release/R88-13545.0.0')


def RunSteps(api):
  hw_test_req = gen_skylab_req('m88_lacros')
  api.skylab.schedule_suites('', [hw_test_req], retry=True)


def GenTests(api):

  def should_enable_retry(check, steps):
    req = api.json.loads(
        steps['schedule skylab tests.buildbucket.schedule'].logs['request'])
    properties = req['requests'][0]['scheduleBuild'].get('properties', [])
    req = properties['requests']['m88_lacros']
    check(req['params']['retry']['allow'])

  yield api.test(
      'with_retry',
      api.buildbucket.simulated_schedule_output(
          builds_service_pb2.BatchResponse(
              responses=[dict(schedule_build=build_pb2.Build(id=1234))]),
          step_name='schedule skylab tests.buildbucket.schedule'),
      api.post_check(should_enable_retry),
  )
