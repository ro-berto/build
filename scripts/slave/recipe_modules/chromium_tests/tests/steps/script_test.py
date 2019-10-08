# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
    'test_utils',
]


def RunSteps(api):
  api.chromium.set_config('chromium')

  test = api.chromium_tests.steps.ScriptTest(
      'script_test',
      'script.py',
      {'script.py': ['compile_target']},
      script_args=['some', 'args'],
      override_compile_targets=['other_target'])

  try:
    test.run(api, '')
  finally:
    api.step('details', [])
    api.step.active_result.presentation.logs['details'] = [
        'compile_targets: %r' % test.compile_targets(),
        'uses_local_devices: %r' % test.uses_local_devices,
    ]


def GenTests(api):
  yield api.test(
      'basic',
      api.properties(mastername='test_mastername', bot_id='test_bot_id'),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
  )

  yield api.test(
      'invalid_results',
      api.properties(mastername='test_mastername', bot_id='test_bot_id'),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
      api.override_step_data('script_test', api.json.output({})),
  )

  yield api.test(
      'failure',
      api.properties(mastername='test_mastername', bot_id='test_bot_id'),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
      api.override_step_data(
          'script_test',
          api.json.output({
              'valid': True,
              'failures': ['TestOne']
          })),
  )
