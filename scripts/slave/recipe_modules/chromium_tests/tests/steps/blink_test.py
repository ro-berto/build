# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'build',
    'chromium',
    'chromium_tests',
    'commit_position',
    'depot_tools/bot_update',
    'depot_tools/tryserver',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'test_results',
    'test_utils',
]


def RunSteps(api):
  api.chromium.set_config(
      'chromium',
      TARGET_PLATFORM=api.properties.get('target_platform', 'linux'))

  test = api.chromium_tests.steps.BlinkTest(extra_args=['--js-flags=--future'])

  try:
    test.run(api, 'with patch')
  finally:
    api.step('details', [])
    api.step.active_result.presentation.logs['details'] = [
        'compile_targets: %r' % test.compile_targets(api),
        'has_valid_results (no suffix): %r' % test.has_valid_results(
            api, ''),
        'uses_local_devices: %r' % test.uses_local_devices,
    ]

  test.run(api, 'without patch')


def GenTests(api):
  yield (
      api.test('android') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          target_platform='android')
  )

  yield (
      api.test('win') +
      api.platform.name('win') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          target_platform='win',
          gs_acl='public')
  )

  yield (
      api.test('unexpected_flakes') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id') +
      api.override_step_data(
          'webkit_layout_tests (with patch)',
          api.test_utils.canned_test_output(
              passing=True, unexpected_flakes=True),
      retcode=0)
  )

  yield (
      api.test('big') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id') +
      api.override_step_data(
          'webkit_layout_tests (with patch)',
          api.test_utils.canned_test_output(
              passing=False, num_additional_failures=125))
  )
