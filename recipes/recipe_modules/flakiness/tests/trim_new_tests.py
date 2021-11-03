# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from RECIPE_MODULES.build.flakiness.api import TestDefinition
from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2

from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import test_result as test_result_pb2

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'flakiness',
    'recipe_engine/assertions',
    'recipe_engine/buildbucket',
    'recipe_engine/step',
]


def RunSteps(api):

  def _generate_test_definition():
    test_result = test_result_pb2.TestResult(
        test_id='random_test_id',
        variant_hash='abc123',
        expected=False,
        status=test_result_pb2.FAIL,
    )
    return TestDefinition(test_result)

  new_tests = []
  for _ in range(15):
    new_tests.append(_generate_test_definition())

  filtered_test = api.flakiness.trim_new_tests(new_tests)
  api.assertions.assertEqual(
      len(filtered_test), api.flakiness._max_test_targets)


def GenTests(api):
  # max_test_targets defaults to 10
  yield api.test(
      'basic',
      api.flakiness(
          check_for_flakiness=True,
          build_count=10,
          historical_query_count=2,
          current_query_count=2,
      ), api.post_process(post_process.DropExpectation))
