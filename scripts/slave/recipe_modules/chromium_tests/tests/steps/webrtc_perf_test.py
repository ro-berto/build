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


def RunSteps(api):
  api.chromium.set_config('chromium')
  api.test_results.set_config('public_server')

  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')

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
      commit_position_property,
      upload_wav_files_from_test=True)

  bot_config = api.chromium_tests.create_bot_config_object(mastername,
                                                           buildername)
  api.chromium_tests.configure_build(bot_config)
  api.chromium_checkout.ensure_checkout(bot_config)

  try:
    test.run(api, '')
  finally:
    api.step('details', [])
    api.step.active_result.presentation.logs['details'] = [
        'compile_targets: %r' % test.compile_targets(api),
        'uses_local_devices: %r' % test.uses_local_devices,
    ]


def GenTests(api):
  typical_properties = api.properties(
        mastername='chromium.webrtc',
        buildername='Linux Tester',
        buildnumber=123,
        bot_id='test_bot_id',
        parent_got_revision='a' * 40)

  yield (
      api.test('webrtc_tester') + typical_properties
  )

  yield (
      # The test will generally not write any files if it succeeds, but the
      # recipe doesn't assume that here.
      api.test('upload_any_wav_files_from_audio_quality_test') +
      typical_properties +
      api.override_step_data('look for wav files',
          api.file.listdir(['rec_1.wav', 'rec_2.wav']), retcode=0)
  )

  yield (
      api.test('upload_any_wav_files_even_if_test_fails') +
      typical_properties +
      api.override_step_data('test_name', retcode=1) +
      api.override_step_data('look for wav files',
          api.file.listdir(['rec_1.wav', 'rec_2.wav']), retcode=0)
  )


  yield (
      api.test('no_upload_if_no_wav_files') +
      typical_properties +
      api.override_step_data('look for wav files',
        api.file.listdir([]), retcode=0)
  )

  yield (
      api.test('webrtc_fyi_tester') +
      api.properties(
          mastername='chromium.webrtc.fyi',
          buildername='Linux Tester',
          buildnumber=123,
          bot_id='test_bot_id',
          parent_got_revision='a' * 40,
          parent_got_cr_revision='builder-chromium-tot')
  )

  yield (
      api.test('webrtc_fyi_experimental_tester') +
      api.properties(
          mastername='chromium.webrtc.fyi.experimental',
          buildername='Linux Tester',
          buildnumber=123,
          bot_id='test_bot_id',
          parent_got_revision='builder-webrtc-tot',
          parent_got_cr_revision='builder-chromium-tot')
  )
