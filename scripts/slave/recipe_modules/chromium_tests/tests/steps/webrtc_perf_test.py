# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import steps

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_checkout',
    'depot_tools/bot_update',
    'recipe_engine/json',
    'recipe_engine/legacy_annotation',
    'recipe_engine/properties',
    'recipe_engine/step',
    'test_results',
    'test_utils',
]


def RunSteps(api):
  api.chromium.set_config('chromium')
  api.test_results.set_config('public_server')

  test = steps.WebRTCPerfTest(
      'test_name', ['some', 'args'],
      'test-perf-id',
      commit_position_property='got_revision_cp')

  bot_config = api.chromium_tests.create_bot_config_object(
      [api.chromium.get_builder_id()])
  api.chromium_tests.configure_build(bot_config)
  api.chromium_checkout.ensure_checkout(bot_config)

  try:
    test.run(api, '')
  finally:
    api.step('details', [])
    api.step.active_result.presentation.logs['details'] = [
        'compile_targets: %r' % test.compile_targets(),
        'uses_local_devices: %r' % test.uses_local_devices,
    ]


def GenTests(api):
  typical_properties = api.properties(parent_got_revision='a' * 40)
  typical_ci_build = api.chromium.ci_build(
      mastername='chromium.webrtc',
      builder='WebRTC Chromium Linux Tester',
  )

  yield api.test(
      'webrtc_tester',
      typical_properties,
      typical_ci_build,
  )

  yield api.test(
      'webrtc_tester_failed',
      typical_properties,
      typical_ci_build,
      api.step_data('test_name', api.legacy_annotation.failure_step),
      api.post_process(post_process.StepFailure, 'test_name'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )
