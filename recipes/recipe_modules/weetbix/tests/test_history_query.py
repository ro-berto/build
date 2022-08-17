# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Tests for query_failure_rate."""
from recipe_engine import post_process

from google.protobuf import timestamp_pb2
from PB.infra.appengine.weetbix.proto.v1 import common as common_weetbix_pb2
from PB.infra.appengine.weetbix.proto.v1 import predicate as predicate_pb2
from PB.infra.appengine.weetbix.proto.v1 import test_history
from PB.infra.appengine.weetbix.proto.v1 import test_verdict

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'weetbix',
    'recipe_engine/json',
    'recipe_engine/raw_io',
    'recipe_engine/step',
]


def RunSteps(api):
  with api.step.nest('nest_parent'):
    test_id = 'ninja://gpu:suite_1/test_one'
    api.weetbix.query_test_history(
        test_id,
        sub_realm='try',
        variant_predicate=predicate_pb2.VariantPredicate(
            contains={'def': {
                'builder': 'some-builder'
            }}),
        partition_time_range=common_weetbix_pb2.TimeRange(
            earliest=timestamp_pb2.Timestamp(seconds=1000),
            latest=timestamp_pb2.Timestamp(seconds=2000)),
        submitted_filter=common_weetbix_pb2.ONLY_SUBMITTED,
        page_size=1000,
        page_token='Some token',
    )


def GenTests(api):
  res = test_history.QueryTestHistoryResponse(
      verdicts=[
          test_verdict.TestVerdict(
              test_id='ninja://gpu:suite_1/test_one',
              variant_hash='dummy_hash',
              invocation_id='invocations/id',
              status=test_verdict.TestVerdictStatus.EXPECTED,
          ),
      ],
      next_page_token='dummy_token')
  test_id = 'ninja://gpu:suite_1/test_one'
  yield api.test(
      'basic',
      api.weetbix.query_test_history(
          res, test_id, parent_step_name='nest_parent'),
      api.post_process(post_process.DropExpectation))
