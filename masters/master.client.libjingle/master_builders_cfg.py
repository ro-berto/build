# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import libjingle_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler

def linux(): return libjingle_factory.LibjingleFactory('src/out', 'linux2')
def mac(): return libjingle_factory.LibjingleFactory('src/out', 'darwin')
def win(): return libjingle_factory.LibjingleFactory('src/build', 'win32')

scheduler_name = 'libjingle_scheduler'
S(scheduler_name, branch='trunk', treeStableTimer=60)

normal_tests = [
    'libjingle_unittest',
    'libjingle_media_unittest',
    'libjingle_sound_unittest',
    'libjingle_p2p_unittest',
]
windows_disabled_tests = [
    'libjingle_p2p_unittest',             # Issue webrtc:1206
]
windows_normal_tests = filter(lambda test: test not in windows_disabled_tests,
                              normal_tests)
memcheck_disabled_tests = [
    'libjingle_media_unittest',           # Issue webrtc:1050
    'libjingle_p2p_unittest',             # Issue webrtc:1050
    'libjingle_peerconnection_unittest',  # Issue webrtc:1204
    'libjingle_unittest',                 # Issue webrtc:1050
]
memcheck_tests = filter(lambda test: test not in memcheck_disabled_tests,
                        normal_tests)
tsan_disabled_tests = [
    'libjingle_media_unittest',           # Issue webrtc:1050
    'libjingle_p2p_unittest',             # Issue webrtc:1050
    'libjingle_peerconnection_unittest',  # Issue webrtc:1205
    'libjingle_unittest',                 # Issue webrtc:1050
]
tsan_tests = filter(lambda test: test not in tsan_disabled_tests,
                    normal_tests)
asan_disabled_tests = [
    'libjingle_p2p_unittest',             # Issue webrtc:1191
]
asan_tests = filter(lambda test: test not in asan_disabled_tests,
                    normal_tests)
asan_gclient_env = {
    'GYP_DEFINES': ('asan=1 release_extra_cflags=-g linux_use_tcmalloc=0 ')}
ninja_options = ['--build-tool=ninja']
win_project = r'..\talk\libjingle_all.sln'
win_factory_prop = {
    'gclient_env': {'GYP_GENERATOR_FLAGS': 'msvs_error_on_missing_sources=1'}}

# Windows.
B('Win32 Debug', 'win32_debug_factory', scheduler=scheduler_name)
F('win32_debug_factory', win().LibjingleFactory(
    target='Debug',
    project=win_project,
    tests=normal_tests,
    factory_properties=win_factory_prop.copy()))

B('Win32 Release', 'win32_release_factory', scheduler=scheduler_name)
F('win32_release_factory', win().LibjingleFactory(
    target='Release',
    project=win_project,
    tests=normal_tests,
    factory_properties=win_factory_prop.copy()))

# Mac.
B('Mac32 Debug', 'mac_debug_factory', scheduler=scheduler_name)
F('mac_debug_factory', mac().LibjingleFactory(
    target='Debug',
    options=ninja_options,
    tests=normal_tests))

B('Mac32 Release', 'mac_release_factory', scheduler=scheduler_name)
F('mac_release_factory', mac().LibjingleFactory(
    target='Release',
    options=ninja_options,
    tests=normal_tests))

B('Mac Asan', 'mac_asan_factory', scheduler=scheduler_name)
F('mac_asan_factory', mac().LibjingleFactory(
    target='Release',
    options=ninja_options,
    tests=asan_tests,
    factory_properties={
        'asan': True,
        'gclient_env': asan_gclient_env.copy(),
    }))

# Linux.
B('Linux32 Debug', 'linux32_debug_factory', scheduler=scheduler_name)
F('linux32_debug_factory', linux().LibjingleFactory(
    target='Debug',
    options=ninja_options,
    tests=normal_tests,
    factory_properties={'gclient_env': {'GYP_DEFINES': 'target_arch=ia32'}}))

B('Linux32 Release', 'linux32_release_factory', scheduler=scheduler_name)
F('linux32_release_factory', linux().LibjingleFactory(
    target='Release',
    options=ninja_options,
    tests=normal_tests,
    factory_properties={'gclient_env': {'GYP_DEFINES': 'target_arch=ia32'}}))

B('Linux64 Debug', 'linux64_debug_factory', scheduler=scheduler_name)
F('linux64_debug_factory', linux().LibjingleFactory(
    target='Debug',
    options=ninja_options,
    tests=normal_tests))

B('Linux64 Release', 'linux64_release_factory', scheduler=scheduler_name)
F('linux64_release_factory', linux().LibjingleFactory(
    target='Release',
    options=ninja_options,
    tests=normal_tests))

B('Linux Clang', 'linux_clang_factory', scheduler=scheduler_name)
F('linux_clang_factory', linux().LibjingleFactory(
    target='Debug',
    options=ninja_options + ['--compiler=clang'],
    tests=normal_tests,
    factory_properties={'gclient_env': {'GYP_DEFINES': 'clang=1'}}))

B('Linux Memcheck', 'linux_memcheck_factory', scheduler=scheduler_name)
F('linux_memcheck_factory', linux().LibjingleFactory(
    target='Release',
    options=ninja_options,
    tests=memcheck_tests,
    factory_properties={
        'needs_valgrind': True,
        'gclient_env': {'GYP_DEFINES': 'build_for_tool=memcheck'},
    }))

B('Linux Tsan', 'linux_tsan_factory', scheduler=scheduler_name)
F('linux_tsan_factory', linux().LibjingleFactory(
    target='Release',
    options=ninja_options,
    tests=tsan_tests,
    factory_properties={
        'needs_valgrind': True,
        'gclient_env': {'GYP_DEFINES': 'build_for_tool=tsan'},
    }))

B('Linux Asan', 'linux_asan_factory', scheduler=scheduler_name)
F('linux_asan_factory', linux().LibjingleFactory(
    target='Release',
    options=ninja_options,
    tests=asan_tests,
    factory_properties={
        'asan': True,
        'gclient_env': asan_gclient_env.copy(),
    }))

# Chrome OS.
B('Chrome OS', 'chromeos_factory', scheduler=scheduler_name)
F('chromeos_factory', linux().LibjingleFactory(
    target='Debug',
    options=ninja_options,
    tests=normal_tests,
    factory_properties={'gclient_env': {'GYP_DEFINES': 'chromeos=1'}}))

def Update(c):
  helper.Update(c)
