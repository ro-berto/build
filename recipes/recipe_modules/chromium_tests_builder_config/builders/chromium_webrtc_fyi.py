# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec


def _chromium_webrtc_fyi_spec(**kwargs):
  return builder_spec.BuilderSpec.create(
      build_gs_bucket='chromium-webrtc', **kwargs)


SPEC = {
    'WebRTC Chromium FYI Android Builder':
        _chromium_webrtc_fyi_spec(
            android_config='base_config',
            chromium_apply_config=['dcheck', 'mb', 'android'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android'
            },
            gclient_apply_config=['android'],
            gclient_config='chromium_webrtc_tot',
            simulation_platform='linux',
        ),
    'WebRTC Chromium FYI Android Builder (dbg)':
        _chromium_webrtc_fyi_spec(
            android_config='base_config',
            chromium_apply_config=['dcheck', 'mb', 'android'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android'
            },
            gclient_apply_config=['android'],
            gclient_config='chromium_webrtc_tot',
            simulation_platform='linux',
        ),
    'WebRTC Chromium FYI Android Builder ARM64 (dbg)':
        _chromium_webrtc_fyi_spec(
            android_config='base_config',
            chromium_apply_config=['dcheck', 'mb', 'android'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android'
            },
            gclient_apply_config=['android'],
            gclient_config='chromium_webrtc_tot',
            simulation_platform='linux',
        ),
    'WebRTC Chromium FYI Android Tests (dbg) (M Nexus5X)':
        _chromium_webrtc_fyi_spec(
            android_config='base_config',
            execution_mode=builder_spec.TEST,
            chromium_apply_config=['dcheck', 'mb', 'android'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android'
            },
            gclient_apply_config=['android'],
            gclient_config='chromium_webrtc_tot',
            parent_buildername='WebRTC Chromium FYI Android Builder ARM64 (dbg)',
            simulation_platform='linux',
        ),
    'WebRTC Chromium FYI Android Tests (dbg) (N Nexus5X)':
        _chromium_webrtc_fyi_spec(
            android_config='base_config',
            execution_mode=builder_spec.TEST,
            chromium_apply_config=['dcheck', 'mb', 'android'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android'
            },
            gclient_apply_config=['android'],
            gclient_config='chromium_webrtc_tot',
            parent_buildername='WebRTC Chromium FYI Android Builder (dbg)',
            simulation_platform='linux',
        ),
    'WebRTC Chromium FYI ios-device':
        _chromium_webrtc_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            gclient_config='ios',
            gclient_apply_config=[],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
            },
            simulation_platform='mac',
        ),
    'WebRTC Chromium FYI ios-simulator':
        _chromium_webrtc_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            gclient_config='ios',
            gclient_apply_config=[],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
            },
            simulation_platform='mac',
        ),
    'WebRTC Chromium FYI Linux Builder':
        _chromium_webrtc_fyi_spec(
            chromium_apply_config=['dcheck', 'mb'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64
            },
            gclient_apply_config=['webrtc_test_resources'],
            gclient_config='chromium_webrtc_tot',
            simulation_platform='linux',
        ),
    'WebRTC Chromium FYI Linux Builder (dbg)':
        _chromium_webrtc_fyi_spec(
            chromium_apply_config=['dcheck', 'mb'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64
            },
            gclient_apply_config=[],
            gclient_config='chromium_webrtc_tot',
            simulation_platform='linux',
        ),
    'WebRTC Chromium FYI Linux Tester':
        _chromium_webrtc_fyi_spec(
            execution_mode=builder_spec.TEST,
            chromium_apply_config=['dcheck', 'mb'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64
            },
            gclient_apply_config=[],
            gclient_config='chromium_webrtc_tot',
            parent_buildername='WebRTC Chromium FYI Linux Builder',
            simulation_platform='linux',
        ),
    'WebRTC Chromium FYI Mac Builder':
        _chromium_webrtc_fyi_spec(
            chromium_apply_config=[
                'dcheck',
                'mb',
                'mac_toolchain',
            ],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64
            },
            gclient_apply_config=['webrtc_test_resources'],
            gclient_config='chromium_webrtc_tot',
            simulation_platform='mac',
        ),
    'WebRTC Chromium FYI Mac Builder (dbg)':
        _chromium_webrtc_fyi_spec(
            chromium_apply_config=[
                'dcheck',
                'mb',
            ],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64
            },
            gclient_apply_config=[],
            gclient_config='chromium_webrtc_tot',
            simulation_platform='mac',
        ),
    'WebRTC Chromium FYI Mac Tester':
        _chromium_webrtc_fyi_spec(
            execution_mode=builder_spec.TEST,
            chromium_apply_config=[
                'dcheck',
                'mb',
                'mac_toolchain',
            ],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64
            },
            gclient_apply_config=[],
            gclient_config='chromium_webrtc_tot',
            parent_buildername='WebRTC Chromium FYI Mac Builder',
            simulation_platform='mac',
        ),
    'WebRTC Chromium FYI Win Builder':
        _chromium_webrtc_fyi_spec(
            chromium_apply_config=['dcheck', 'mb'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32
            },
            gclient_apply_config=['webrtc_test_resources'],
            gclient_config='chromium_webrtc_tot',
            simulation_platform='win',
        ),
    'WebRTC Chromium FYI Win Builder (dbg)':
        _chromium_webrtc_fyi_spec(
            chromium_apply_config=['dcheck', 'mb'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32
            },
            gclient_apply_config=[],
            gclient_config='chromium_webrtc_tot',
            simulation_platform='win',
        ),
    'WebRTC Chromium FYI Win10 Tester':
        _chromium_webrtc_fyi_spec(
            execution_mode=builder_spec.TEST,
            chromium_apply_config=['dcheck', 'mb'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32
            },
            gclient_apply_config=[],
            gclient_config='chromium_webrtc_tot',
            parent_buildername='WebRTC Chromium FYI Win Builder',
            simulation_platform='win',
        ),
}
