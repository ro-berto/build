# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_checkout',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/gsutil',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'test_results',
    'test_utils',
    'zip',
]


PERF_CONFIG_MAPPINGS = {
  'r_chromium': 'got_cr_revision',
  'r_chromium_commit_pos': 'got_cr_revision_cp',
}

from recipe_engine import post_process

def RunSteps(api):
  api.chromium.set_config('chromium')
  api.test_results.set_config('public_server')

  mastername = api.properties.get('mastername')
  buildername = api.buildbucket.build.builder.builder

  if 'fyi' in mastername:
    perf_config_mappings = PERF_CONFIG_MAPPINGS
    commit_position_property = 'got_cr_revision_cp'
  else:
    perf_config_mappings = {}
    commit_position_property = 'got_revision_cp'

  test = api.chromium_tests.steps.WebRTCPerfTest(
      'test_name',
      ['some', 'args'],
      'test-perf-id',
      perf_config_mappings,
      commit_position_property)

  bot_config = api.chromium_tests.create_bot_config_object(
      [api.chromium_tests.create_bot_id(mastername, buildername)])
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
  typical_properties = api.properties(
      mastername='chromium.webrtc',
      bot_id='test_bot_id',
      parent_got_revision='a' * 40)
  typical_ci_build = api.buildbucket.ci_build(
      project='chromium',
      git_repo='https://chromium.googlesource.com/chromium/src',
      builder='WebRTC Chromium Linux Tester',
      build_number=123,
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
      api.step_data('test_name', retcode=1),
      api.post_process(post_process.StepFailure, 'test_name'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'webrtc_fyi_tester',
      api.properties(
          mastername='chromium.webrtc.fyi',
          bot_id='test_bot_id',
          parent_got_revision='a' * 40,
          parent_got_cr_revision='builder-chromium-tot'),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='WebRTC Chromium FYI Linux Tester',
          build_number=123,
      ),
  )
