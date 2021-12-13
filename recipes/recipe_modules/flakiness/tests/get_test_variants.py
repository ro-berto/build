# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import common as resultdb_common
from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import test_result as test_result_pb2

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'flakiness',
    'recipe_engine/assertions',
    'recipe_engine/resultdb',
    'recipe_engine/step',
]


def RunSteps(api):
  inv_list = ['invocations/1']
  test_results = api.flakiness.get_test_variants(inv_list)
  r = test_results.pop()
  api.assertions.assertTrue(r.is_experimental)


def GenTests(api):

  def _generate_tag(key, value):
    sp = resultdb_common.StringPair()
    sp.key = key
    sp.value = value
    return sp

  def _generate_variant(**kwargs):
    variant = resultdb_common.Variant()
    variant_def = getattr(variant, 'def')
    for k, v in kwargs.items():
      variant_def[str(k)] = str(v)
    return variant

  def _generate_test_result(test_id, variant, variant_hash, tags, status=None):
    return test_result_pb2.TestResult(
        test_id=test_id,
        variant=variant,
        variant_hash=variant_hash,
        tags=tags,
        expected=False,
        status=status,
    )

  current_patchset_invocations = {}
  test_results = [
      _generate_test_result(
          'ninja://some/test/TestSuite.test_a',
          _generate_variant(
              os='Mac-11',
              test_suite='ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4'
          ),
          'random_hash',
          [_generate_tag('step_name', 'something (experimental)')],
      )
  ]
  current_patchset_invocations['invocations/1'] = api.resultdb.Invocation(
      test_results=test_results)

  yield api.test(
      'basic',
      api.flakiness(check_for_flakiness=True),
      api.resultdb.query(
          inv_bundle=current_patchset_invocations,
          step_name=('fetch test variants from ResultDB')),
      api.post_process(post_process.DropExpectation),
  )
