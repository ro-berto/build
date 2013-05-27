# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import webrtc_factory

defaults = {}


def ConfigureBuilders(c, svn_url, branch, custom_deps_list=None):
  def win():
    return webrtc_factory.WebRTCFactory('src/out', 'win32', svn_url,
                                        branch, custom_deps_list)
  helper = master_config.Helper(defaults)
  B = helper.Builder
  F = helper.Factory
  S = helper.Scheduler

  scheduler = 'webrtc_win_scheduler'
  S(scheduler, branch=branch, treeStableTimer=0)

  normal_tests = [
      'audio_coding_module_test',
      'audio_coding_unittests',
      'audio_decoder_unittests',
      'audioproc_unittest',
      'bitrate_controller_unittests',
      'channel_transport_unittests',
      'common_video_unittests',
      'media_file_unittests',
      'metrics_unittests',
      'neteq_unittests',
      'resampler_unittests',
      'rtp_rtcp_unittests',
      'signal_processing_unittests',
      'system_wrappers_unittests',
      'remote_bitrate_estimator_unittests',
      'test_fec',
      'test_support_unittests',
      'vad_unittests',
      'video_coding_integrationtests',
      'video_coding_unittests',
      'video_engine_core_unittests',
      'video_processing_unittests',
      'voice_engine_unittests',
      'vp8_integrationtests',
      'vp8_unittests',
      'webrtc_utility_unittests',
  ]
  win64_disabled_tests = [
      'audio_coding_unittests',   # webrtc:1458.
      'audio_decoder_unittests',  # webrtc:1459.
      'audioproc_unittest',       # webrtc:1461.
      'neteq_unittests',          # webrtc:1460.
  ]
  win64_tests = filter(lambda test: test not in win64_disabled_tests,
                       normal_tests)

  ninja_options = ['--build-tool=ninja']

  defaults['category'] = 'win'

  B('Win32 Debug', 'win32_debug_factory', scheduler=scheduler)
  F('win32_debug_factory', win().WebRTCFactory(
      target='Debug',
      options=ninja_options,
      tests=normal_tests))

  B('Win32 Release', 'win32_release_factory', scheduler=scheduler)
  F('win32_release_factory', win().WebRTCFactory(
      target='Release',
      options=ninja_options,
      tests=normal_tests,
      # No point having more than one bot complaining about missing sources.
      factory_properties={
          'gclient_env': {
              'GYP_GENERATOR_FLAGS': 'msvs_error_on_missing_sources=1',
          },
      }))

  B('Win64 Debug', 'win64_debug_factory', scheduler=scheduler)
  F('win64_debug_factory', win().WebRTCFactory(
      target='Debug_x64',
      options=ninja_options,
      tests=win64_tests,
      factory_properties={
          'gclient_env': {'GYP_DEFINES': 'target_arch=x64'},
      }))

  B('Win64 Release', 'win64_release_factory', scheduler=scheduler)
  F('win64_release_factory', win().WebRTCFactory(
      target='Release_x64',
      options=ninja_options,
      tests=win64_tests,
      factory_properties={
          'gclient_env': {'GYP_DEFINES': 'target_arch=x64'},
      }))

  helper.Update(c)
