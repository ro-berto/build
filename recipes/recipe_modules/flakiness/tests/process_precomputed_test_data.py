# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'flakiness',
    'recipe_engine/assertions',
]


def RunSteps(api):
  excluded_invs = set(['invocations/1', 'invocations/2'])
  test_data = [{
      'test_id': 'ninja://some/test:module/TestSuite.test_a',
      'variant_hash': 'test_a',
      'invocation': ['invocations/4'],
  }, {
      'test_id': 'ninja://some/test:module/TestSuite.test_b',
      'variant_hash': 'test_b',
      'invocation': ['invocations/1'],
  }, {
      'test_id': 'ninja://some/test:module/TestSuite.test_c',
      'variant_hash': 'test_c',
      'invocation': ['invocations/2', 'invocations/5', 'invocations/6'],
  }]
  tests = api.flakiness.process_precomputed_test_data(test_data, excluded_invs)
  api.assertions.assertEqual(len(tests), 2)
  api.assertions.assertTrue(('ninja://some/test:module/TestSuite.test_a',
                             'test_a') in tests)
  api.assertions.assertTrue(('ninja://some/test:module/TestSuite.test_c',
                             'test_c') in tests)


def GenTests(api):
  yield api.test(
      'basic',
      api.post_process(post_process.DropExpectation),
  )
