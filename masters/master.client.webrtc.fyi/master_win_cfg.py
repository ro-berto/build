# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import webrtc_factory

defaults = {}


def win():
  return webrtc_factory.WebRTCFactory('src/out', 'win32')

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler

scheduler = 'webrtc_win_scheduler'
S(scheduler, branch='trunk', treeStableTimer=0)

tests = [
    'audio_decoder_unittests',
    'common_audio_unittests',
    'common_video_unittests',
    'libjingle_media_unittest',
    'libjingle_p2p_unittest',
    'libjingle_peerconnection_unittest',
    'libjingle_sound_unittest',
    'libjingle_unittest',
    'modules_tests',
    'modules_unittests',
    'neteq_unittests',
    'system_wrappers_unittests',
    'test_support_unittests',
    'tools_unittests',
    'video_engine_core_unittests',
    'video_engine_tests',
    'voice_engine_unittests',
]

ninja_options = ['--build-tool=ninja']
dr_memory_factory_properties = {
   'gclient_env': {'GYP_DEFINES': 'build_for_tool=drmemory'},
   'needs_drmemory': True,
}

defaults['category'] = 'win'

B('Win DrMemory Light', 'win_drmemory_light_factory', scheduler=scheduler)
F('win_drmemory_light_factory', win().WebRTCFactory(
    target='Debug',
    options=ninja_options,
    tests=['drmemory_light_' + test for test in tests],
    factory_properties=dr_memory_factory_properties))

B('Win DrMemory Full', 'win_drmemory_full_factory', scheduler=scheduler)
F('win_drmemory_full_factory', win().WebRTCFactory(
    target='Debug',
    options=ninja_options,
    tests=['drmemory_full_' + test for test in tests],
    factory_properties=dr_memory_factory_properties))

B('Win DrMemory Pattern', 'win_drmemory_pattern_factory', scheduler=scheduler)
F('win_drmemory_pattern_factory', win().WebRTCFactory(
    target='Debug',
    options=ninja_options,
    tests=['drmemory_pattern_' + test for test in tests],
    factory_properties=dr_memory_factory_properties))

B('Win SyzyASan', 'win_asan_factory', scheduler=scheduler)
F('win_asan_factory', win().WebRTCFactory(
    target='Release',
    options=ninja_options,
    tests=tests,
    factory_properties={
        'asan': True,
        'gclient_env': {
            'GYP_DEFINES': ('syzyasan=1 win_z7=1 chromium_win_pch=0 '
                            'component=static_library'),
            'GYP_USE_SEPARATE_MSPDBSRV': '1',
        },
    }))

B('Win Tsan', 'win_tsan_factory', scheduler=scheduler)
F('win_tsan_factory', win().WebRTCFactory(
    target='Debug',
    options=ninja_options,
    tests=['tsan_' + test for test in tests],
    factory_properties={
        'needs_tsan_win': True,
        'gclient_env': { 'GYP_DEFINES' : 'build_for_tool=tsan' },
    }))


def Update(c):
  helper.Update(c)
