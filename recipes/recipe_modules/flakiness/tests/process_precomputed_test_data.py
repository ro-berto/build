# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'flakiness',
    'recipe_engine/assertions',
]


def RunSteps(api):
  excluded_invs = set(['invocations/1', 'invocations/2'])
  test_data = [{
      'test_id': 'ninja://some/test:module/TestSuite.test_a',
      'variant': ('[{"key": "builder", "value":"builder_name"},'
                  '{"key":"os", "value":"Mac-11.0"},'
                  '{"key":"test_suite","value":"module_iPhone 11 14.4"}]'),
      'variant_hash': 'test_a',
      'invocation': ['invocations/4'],
      'is_experimental': True
  }, {
      'test_id': 'ninja://some/test:module/TestSuite.test_b',
      'variant': ('[{"key": "builder", "value":"builder_name"},'
                  '{"key":"os", "value":"Mac-11.0"},'
                  '{"key":"test_suite","value":"module_iPhone 11 14.4"}]'),
      'variant_hash': 'test_b',
      'invocation': ['invocations/1'],
      'is_experimental': False
  }, {
      'test_id': 'ninja://some/test:module/TestSuite.test_c',
      'variant': ('[{"key": "builder", "value":"builder_name"},'
                  '{"key":"os", "value":"Mac-11.0"},'
                  '{"key":"test_suite","value":"module_iPhone 11 14.4"}]'),
      'variant_hash': 'test_c',
      'invocation': ['invocations/2', 'invocations/5', 'invocations/6'],
      'is_experimental': False
  }]
  tests = api.flakiness.process_precomputed_test_data(test_data, excluded_invs)
  api.assertions.assertEqual(len(tests), 2)
  api.assertions.assertTrue(('ninja://some/test:module/TestSuite.test_a',
                             'test_a', True) in tests)
  api.assertions.assertTrue(('ninja://some/test:module/TestSuite.test_c',
                             'test_c', False) in tests)


def GenTests(api):
  yield api.test(
      'basic',
      api.post_process(post_process.DropExpectation),
  )
