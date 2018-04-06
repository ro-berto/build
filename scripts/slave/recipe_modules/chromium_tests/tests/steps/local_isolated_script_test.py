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
  test = api.chromium_tests.steps.LocalIsolatedScriptTest(
      'base_unittests',
      override_compile_targets=api.properties.get('override_compile_targets'))

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
