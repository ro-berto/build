# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/properties',
    'skylab',
]

from RECIPE_MODULES.build.skylab import structs

from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import (builds_service as
                                                       builds_service_pb2)
from recipe_engine import post_process


def gen_skylab_req(tag, retries):
  return structs.SkylabRequest.create(
      request_tag=tag,
      board='eve',
      tast_expr='lacros.Basic',
      retries=retries,
      cros_img='eve-release/R88-13545.0.0')


def RunSteps(api):
  hw_test_req = gen_skylab_req('m88_lacros', api.properties.get('retries'))
  api.skylab.schedule_suites('', [hw_test_req])


def GenTests(api):

  def should_enable_retry(check, steps, retries):
    req = api.json.loads(
        steps['schedule skylab tests.buildbucket.schedule'].logs['request'])
    properties = req['requests'][0]['scheduleBuild'].get('properties', [])
    req = properties['requests']['m88_lacros']
    check(req['params']['retry']['allow'])
    check(req['params']['retry']['max'] == retries)

  yield api.test(
      'with_retry',
      api.properties(retries=3),
      api.buildbucket.simulated_schedule_output(
          builds_service_pb2.BatchResponse(
              responses=[dict(schedule_build=build_pb2.Build(id=1234))]),
          step_name='schedule skylab tests.buildbucket.schedule'),
      api.post_check(should_enable_retry, 3),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'exceed_max_retries',
      api.properties(retries=6),
      api.expect_exception('ValueError'),
      api.post_process(
          post_process.ResultReasonRE,
          r'Uncaught Exception: ValueError\b.*\bretries\b.* must be in '
          r'\(0, 1, 2, 3, 4, 5\) \(got 6\)'),
      api.post_process(post_process.DropExpectation),
  )
