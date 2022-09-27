# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Tests for query_variants."""
from recipe_engine import post_process

from PB.go.chromium.org.luci.analysis.proto.v1 import common as common_pb2
from PB.go.chromium.org.luci.analysis.proto.v1 import test_history

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'weetbix',
    'recipe_engine/step',
]


def RunSteps(api):
  with api.step.nest('nest_parent'):
    test_id = 'ninja://gpu:suite_1/test_one'
    variants, next_page_token = api.weetbix.query_variants(test_id)
    assert variants
    assert next_page_token is None


def GenTests(api):
  res = test_history.QueryVariantsResponse(variants=[
      test_history.QueryVariantsResponse.VariantInfo(
          variant_hash='dummy_hash',
          variant=common_pb2.Variant(**{"def": {
              'foo': 'bar'
          }}),
      )
  ])
  test_id = 'ninja://gpu:suite_1/test_one'
  yield api.test(
      'basic',
      api.weetbix.query_variants(res, test_id, parent_step_name='nest_parent'),
      api.post_check(
          post_process.LogContains,
          'nest_parent.Test history query_variants rpc call for %s' % test_id,
          'json.output', ['dummy_hash', '"foo": "bar"']),
      api.post_process(post_process.DropExpectation),
  )