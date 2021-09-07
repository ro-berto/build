# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec


def _chromium_webrtc_spec(**kwargs):
  return builder_spec.BuilderSpec.create(
      build_gs_bucket='chromium-webrtc', **kwargs)


SPEC = {
    'WebRTC Chromium Android Builder':
        _chromium_webrtc_spec(
            android_config='base_config',
            chromium_apply_config=['dcheck', 'mb', 'android'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android'
            },
            gclient_apply_config=['android'],
            gclient_config='chromium_webrtc',
            simulation_platform='linux',
        ),
    'WebRTC Chromium Android Tester':
        _chromium_webrtc_spec(
            android_config='base_config',
            execution_mode=builder_spec.TEST,
            chromium_apply_config=['dcheck', 'mb', 'android'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android'
            },
            gclient_apply_config=['android'],
            gclient_config='chromium_webrtc',
            parent_buildername='WebRTC Chromium Android Builder',
            test_results_config='public_server',
            simulation_platform='linux',
        ),
    'WebRTC Chromium Linux Builder':
        _chromium_webrtc_spec(
            chromium_apply_config=['dcheck', 'mb'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64
            },
            gclient_apply_config=['webrtc_test_resources'],
            gclient_config='chromium_webrtc',
            simulation_platform='linux',
        ),
    'WebRTC Chromium Linux Tester':
        _chromium_webrtc_spec(
            execution_mode=builder_spec.TEST,
            chromium_apply_config=['dcheck', 'mb'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64
            },
            gclient_apply_config=['webrtc_test_resources'],
            gclient_config='chromium_webrtc',
            parent_buildername='WebRTC Chromium Linux Builder',
            test_results_config='public_server',
            simulation_platform='linux',
        ),
    'WebRTC Chromium Mac Builder':
        _chromium_webrtc_spec(
            chromium_apply_config=['dcheck', 'mb'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64
            },
            gclient_apply_config=['webrtc_test_resources'],
            gclient_config='chromium_webrtc',
            simulation_platform='mac',
        ),
    'WebRTC Chromium Mac Tester':
        _chromium_webrtc_spec(
            execution_mode=builder_spec.TEST,
            chromium_apply_config=['dcheck', 'mb'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64
            },
            gclient_apply_config=['webrtc_test_resources'],
            gclient_config='chromium_webrtc',
            parent_buildername='WebRTC Chromium Mac Builder',
            test_results_config='public_server',
            simulation_platform='mac',
        ),
    'WebRTC Chromium Win Builder':
        _chromium_webrtc_spec(
            chromium_apply_config=['dcheck', 'mb'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32
            },
            gclient_apply_config=['webrtc_test_resources'],
            gclient_config='chromium_webrtc',
            simulation_platform='win',
        ),
    'WebRTC Chromium Win10 Tester':
        _chromium_webrtc_spec(
            execution_mode=builder_spec.TEST,
            chromium_apply_config=['dcheck', 'mb'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32
            },
            gclient_apply_config=['webrtc_test_resources'],
            gclient_config='chromium_webrtc',
            parent_buildername='WebRTC Chromium Win Builder',
            test_results_config='public_server',
            simulation_platform='win',
        ),
    'WebRTC Chromium Win7 Tester':
        _chromium_webrtc_spec(
            execution_mode=builder_spec.TEST,
            chromium_apply_config=['dcheck', 'mb'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32
            },
            gclient_apply_config=['webrtc_test_resources'],
            gclient_config='chromium_webrtc',
            parent_buildername='WebRTC Chromium Win Builder',
            test_results_config='public_server',
            simulation_platform='win',
        ),
    'WebRTC Chromium Win8 Tester':
        _chromium_webrtc_spec(
            execution_mode=builder_spec.TEST,
            chromium_apply_config=['dcheck', 'mb'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32
            },
            gclient_apply_config=['webrtc_test_resources'],
            gclient_config='chromium_webrtc',
            parent_buildername='WebRTC Chromium Win Builder',
            test_results_config='public_server',
            simulation_platform='win',
        ),
}
