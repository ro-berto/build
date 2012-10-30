# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import webrtc_factory

defaults = {}


def ConfigureBuilders(c, svn_url, branch, category, custom_deps_list=None):
  def mac():
    return webrtc_factory.WebRTCFactory('src/build', 'darwin', svn_url,
                                        branch, custom_deps_list)
  helper = master_config.Helper(defaults)
  B = helper.Builder
  F = helper.Factory
  S = helper.Scheduler

  scheduler = 'webrtc_%s_mac_scheduler' % category
  S(scheduler, branch=branch, treeStableTimer=0, categories=[category])

  normal_tests = ['audio_coding_module_test',
                  'audio_coding_unittests',
                  'audio_conference_mixer_unittests',
                  'audio_device_test_api',
                  'audioproc_unittest',
                  'bitrate_controller_unittests',
                  'common_video_unittests',
                  'cng_unittests',
                  'g711_unittests',
                  'g722_unittests',
                  'isacfix_unittests',
                  'media_file_unittests',
                  'metrics_unittests',
                  'neteq_unittests',
                  'pcm16b_unittests',
                  'resampler_unittests',
                  'rtp_rtcp_unittests',
                  'signal_processing_unittests',
                  'system_wrappers_unittests',
                  'remote_bitrate_estimator_unittests',
                  'test_fec',
                  'test_support_unittests',
                  'udp_transport_unittests',
                  'vad_unittests',
                  'video_codecs_test_framework_integrationtests',
                  'video_codecs_test_framework_unittests',
                  'video_coding_unittests',
                  'video_engine_core_unittests',
                  'video_processing_unittests',
                  'voice_engine_unittests',
                  'vp8_integrationtests',
                  'vp8_unittests',
                  'webrtc_utility_unittests',]

  memcheck_disabled_tests = [
      'audio_coding_module_test', # Issue 270
      'test_fec',                 # Too slow for memcheck
  ]
  memcheck_tests = filter(lambda test: test not in memcheck_disabled_tests,
                          normal_tests)
  tsan_disabled_tests = [
      'audio_coding_module_test',   # Issue 283
      'audioproc_unittest',         # Issue 299
      'system_wrappers_unittests',  # Issue 300
      'video_processing_unittests', # Issue 303
      'test_fec',                   # Too slow for TSAN
  ]
  tsan_tests = filter(lambda test: test not in tsan_disabled_tests,
                      normal_tests)
  asan_disabled_tests = [
      'audio_coding_module_test', # Issue 281
      'neteq_unittests',          # Issue 282
  ]
  asan_tests = filter(lambda test: test not in asan_disabled_tests,
                      normal_tests)
  options = ['--', '-project', '../webrtc.xcodeproj']

  defaults['category'] = category

  B('Mac32Debug', 'mac_debug_factory', scheduler=scheduler)
  F('mac_debug_factory', mac().WebRTCFactory(
      target='Debug',
      options=options,
      tests=normal_tests))
  B('Mac32Release', 'mac_release_factory', scheduler=scheduler)
  F('mac_release_factory', mac().WebRTCFactory(
      target='Release',
      options=options,
      tests=normal_tests))
  B('MacMemcheck', 'mac_memcheck_factory', scheduler=scheduler)
  F('mac_memcheck_factory', mac().WebRTCFactory(
      target='Release',
      options=options,
      tests=['memcheck_' + test for test in memcheck_tests],
      factory_properties={'needs_valgrind': True,
                          'gclient_env':
                          {'GYP_DEFINES': 'build_for_tool=memcheck'}}))
  B('MacTsan', 'mac_tsan_factory', scheduler=scheduler)
  F('mac_tsan_factory', mac().WebRTCFactory(
      target='Release',
      options=options,
      tests=['tsan_' + test for test in tsan_tests],
      factory_properties={'needs_valgrind': True,
                          'gclient_env':
                          {'GYP_DEFINES': 'build_for_tool=tsan'}}))
  B('MacAsan', 'mac_asan_factory', scheduler=scheduler)
  F('mac_asan_factory', mac().WebRTCFactory(
      target='Release',
      options=options,
      tests=asan_tests,
      factory_properties={'asan': True,
                          'gclient_env':
                          {'GYP_DEFINES': ('asan=1'
                                           ' release_extra_cflags=-g '
                                           ' linux_use_tcmalloc=0 ')}}))
  helper.Update(c)
