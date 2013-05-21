# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import webrtc_factory

defaults = {}


def ConfigureBuilders(c, svn_url, branch, custom_deps_list=None):
  def mac():
    return webrtc_factory.WebRTCFactory('src/xcodebuild', 'darwin', svn_url,
                                        branch, custom_deps_list)
  def macIos():
    return webrtc_factory.WebRTCFactory('', 'darwin', svn_url, branch,
                                        nohooks_on_update=True)

  helper = master_config.Helper(defaults)
  B = helper.Builder
  F = helper.Factory
  S = helper.Scheduler

  scheduler = 'webrtc_mac_scheduler'
  S(scheduler, branch=branch, treeStableTimer=0)

  tests = [
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

  options = ['--', '-project', '../webrtc.xcodeproj']

  defaults['category'] = 'mac'

  B('Mac32 Debug', 'mac_debug_factory', scheduler=scheduler)
  F('mac_debug_factory', mac().WebRTCFactory(
      target='Debug',
      options=options,
      tests=tests))

  B('Mac32 Release', 'mac_release_factory', scheduler=scheduler)
  F('mac_release_factory', mac().WebRTCFactory(
      target='Release',
      options=options,
      tests=tests))

  B('Mac64 Debug', 'mac64_debug_factory', scheduler=scheduler)
  F('mac64_debug_factory', mac().WebRTCFactory(
      target='Debug',
      options=options,
      tests=tests,
      factory_properties={
          'gclient_env': {'GYP_DEFINES': 'host_arch=x64 target_arch=x64'}
      }))

  B('Mac64 Release', 'mac64_release_factory', scheduler=scheduler)
  F('mac64_release_factory', mac().WebRTCFactory(
      target='Release',
      options=options,
      tests=tests,
      factory_properties={
          'gclient_env': {'GYP_DEFINES': 'host_arch=x64 target_arch=x64'}
      }))

  B('Mac Asan', 'mac_asan_factory', scheduler=scheduler)
  F('mac_asan_factory', mac().WebRTCFactory(
      target='Release',
      options=options,
      tests=tests,
      factory_properties={'asan': True,
                          'gclient_env':
                          {'GYP_DEFINES': ('asan=1'
                                           ' release_extra_cflags=-g '
                                           ' linux_use_tcmalloc=0 ')}}))

  # iOS.
  B('iOS Device', 'ios_release_factory', scheduler=scheduler)
  F('ios_release_factory', macIos().ChromiumAnnotationFactory(
      target='Release',
      slave_type='AnnotatedBuilderTester',
      annotation_script='src/webrtc/build/ios-webrtc.sh'))

  helper.Update(c)
