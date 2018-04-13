# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_tests',
    'isolate',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/step',
    'test_utils',
]


def RunSteps(api):
  test_name = api.properties.get('test_name') or 'base_unittests'

  test = api.chromium_tests.steps.LocalIsolatedScriptTest(
      test_name,
      override_compile_targets=api.properties.get('override_compile_targets'))

  test_repeat_count = api.properties.get('repeat_count')
  if test_repeat_count:
      test.test_options = api.chromium_tests.steps.TestOptions(
          test_filter=api.properties.get('test_filter'),
          repeat_count=test_repeat_count,
          retry_limit=0,
          run_disabled=bool(test_repeat_count)
      )

  test.pre_run(api, '')
  test.run(api, '')
  test.post_run(api, '')

  api.step('details', [])
  api.step.active_result.presentation.logs['details'] = [
      'compile_targets: %r' % test.compile_targets(api),
      'isolate_target: %r' % test.isolate_target(api),
      'uses_local_devices: %r' % test.uses_local_devices,
      'uses_isolate: %r' % test.uses_isolate,
  ]


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          })
  )

  yield (
      api.test('override_compile_targets') +
      api.properties(
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          override_compile_targets=['base_unittests_run'])
  )

  yield (
      api.test('customized_test_options') +
      api.properties(
          swarm_hashes={
            'webkit_layout_tests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          test_filter=['test1', 'test2'],
          repeat_count=20,
          test_name='webkit_layout_tests')
  )
