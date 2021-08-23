# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import steps

DEPS = [
    'build',
    'chromium',
    'chromium_tests',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'test_utils',
]


def RunSteps(api):
  api.chromium.set_config('chromium')

  test_spec = steps.ScriptTestSpec.create(
      'script_test',
      script='script.py',
      all_compile_targets={'script.py': ['compile_target']},
      script_args=['some', 'args'],
      override_compile_targets=api.properties.get('override_compile_targets'))
  test = test_spec.get_test()

  try:
    test.run(api, '')
    inv_names = test.get_invocation_names('')
    if inv_names:
      assert inv_names[0] == 'test-invocation', inv_names[0]
  finally:
    api.step('details', [])
    api.step.active_result.presentation.logs['details'] = [
        'compile_targets: {!r}'.format(test.compile_targets()),
        'uses_local_devices: {!r}'.format(test.uses_local_devices),
    ]


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
  )

  yield api.test(
      'override_compile_targets',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(override_compile_targets=['other_target']),
  )

  yield api.test(
      'invalid_results',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.override_step_data('script_test', api.json.output({})),
  )

  yield api.test(
      'with_invocation',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.override_step_data(
          'script_test',
          api.json.output({
              'valid': True,
              'failures': ['']
          }),
          stderr=api.raw_io.output(
              'rdb-stream: included "test-invocation" in "build-invocation"')),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failure',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.override_step_data(
          'script_test',
          api.json.output({
              'valid': True,
              'failures': ['TestOne']
          })),
  )
