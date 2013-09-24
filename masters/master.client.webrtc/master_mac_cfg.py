# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import webrtc_factory

defaults = {}


def mac():
  return webrtc_factory.WebRTCFactory('src/out', 'darwin')

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler

scheduler = 'webrtc_mac_scheduler'
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
    'metrics_unittests',
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

baremetal_tests = [
    'audio_device_tests',
    'video_capture_tests',
    'video_engine_tests',
    'vie_auto_test',
    'voe_auto_test',
]
options = ['--build-tool=ninja']

mac_ios_factory_properties = {
    'gclient_deps': 'ios',
    'gclient_env': {
        'GYP_CROSSCOMPILE': '1',
        'GYP_DEFINES': ('build_with_libjingle=1 OS=ios target_arch=armv7 '
                        'key_id=""'),
    }
}

defaults['category'] = 'mac'

B('Mac32 Debug', 'mac_debug_factory', scheduler=scheduler, auto_reboot=False)
F('mac_debug_factory', mac().WebRTCFactory(
    target='Debug',
    options=options,
    tests=tests))

B('Mac32 Release', 'mac_release_factory', scheduler=scheduler,
  auto_reboot=False)
F('mac_release_factory', mac().WebRTCFactory(
    target='Release',
    options=options,
    tests=tests))

B('Mac64 Debug', 'mac64_debug_factory', scheduler=scheduler, auto_reboot=False)
F('mac64_debug_factory', mac().WebRTCFactory(
    target='Debug',
    options=options,
    tests=tests,
    factory_properties={
        'gclient_env': {'GYP_DEFINES': 'host_arch=x64 target_arch=x64'}
    }))

B('Mac64 Release', 'mac64_release_factory', scheduler=scheduler,
  auto_reboot=False)
F('mac64_release_factory', mac().WebRTCFactory(
    target='Release',
    options=options,
    tests=tests,
    factory_properties={
        'gclient_env': {'GYP_DEFINES': 'host_arch=x64 target_arch=x64'}
    }))

B('Mac Asan', 'mac_asan_factory', scheduler=scheduler, auto_reboot=False)
F('mac_asan_factory', mac().WebRTCFactory(
    target='Release',
    options=options,
    tests=tests,
    factory_properties={'asan': True,
                        'gclient_env':
                        {'GYP_DEFINES': ('asan=1'
                                         ' release_extra_cflags=-g '
                                         ' linux_use_tcmalloc=0 ')}}))

B('Mac32 Release [large tests]', 'mac_largetests_factory',
  scheduler=scheduler, auto_reboot=True)
F('mac_largetests_factory', mac().WebRTCFactory(
    target='Release',
    options=options,
    tests=baremetal_tests,
    factory_properties={
        'virtual_webcam': True,
        'show_perf_results': True,
        'expectations': True,
        'perf_id': 'webrtc-mac-large-tests',
        'perf_measuring_tests': ['vie_auto_test',
                                 'video_engine_tests'],
        'custom_cmd_line_tests': ['vie_auto_test',
                                  'voe_auto_test'],
    }))

# iOS.
B('iOS Debug', 'ios_debug_factory', scheduler=scheduler, auto_reboot=False)
F('ios_debug_factory', mac().WebRTCFactory(
    target='Debug',
    options=options,
    factory_properties=mac_ios_factory_properties))


def Update(c):
  helper.Update(c)
