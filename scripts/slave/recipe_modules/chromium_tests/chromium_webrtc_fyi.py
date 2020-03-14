# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import bot_spec

SPEC = {
    'settings': {
        'build_gs_bucket': 'chromium-webrtc'
    },
    'builders': {
        'WebRTC Chromium FYI Android Builder':
            bot_spec.BotSpec.create(
                android_config='base_config',
                bot_type=bot_spec.BUILDER_TESTER,
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
                set_component_rev={
                    'name': 'src/third_party/webrtc',
                    'rev_str': '%s'
                },
                testing={'platform': 'linux'}),
        'WebRTC Chromium FYI Android Builder (dbg)':
            bot_spec.BotSpec.create(
                android_config='base_config',
                bot_type=bot_spec.BUILDER,
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
                set_component_rev={
                    'name': 'src/third_party/webrtc',
                    'rev_str': '%s'
                },
                testing={'platform': 'linux'}),
        'WebRTC Chromium FYI Android Builder ARM64 (dbg)':
            bot_spec.BotSpec.create(
                android_config='base_config',
                bot_type=bot_spec.BUILDER,
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
                set_component_rev={
                    'name': 'src/third_party/webrtc',
                    'rev_str': '%s'
                },
                testing={'platform': 'linux'}),
        'WebRTC Chromium FYI Android Tests (dbg) (K Nexus5)':
            bot_spec.BotSpec.create(
                android_config='base_config',
                bot_type=bot_spec.TESTER,
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
                set_component_rev={
                    'name': 'src/third_party/webrtc',
                    'rev_str': '%s'
                },
                test_results_config='public_server',
                testing={'platform': 'linux'},
            ),
        'WebRTC Chromium FYI Android Tests (dbg) (M Nexus5X)':
            bot_spec.BotSpec.create(
                android_config='base_config',
                bot_type=bot_spec.TESTER,
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
                parent_buildername=
                'WebRTC Chromium FYI Android Builder ARM64 (dbg)',
                set_component_rev={
                    'name': 'src/third_party/webrtc',
                    'rev_str': '%s'
                },
                test_results_config='public_server',
                testing={'platform': 'linux'},
            ),
        'WebRTC Chromium FYI ios-device':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mac_toolchain',
                ],
                chromium_tests_apply_config=[],
                gclient_config='ios',
                gclient_apply_config=[],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'ios',
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'mac',
                },
            ),
        'WebRTC Chromium FYI ios-simulator':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mac_toolchain',
                ],
                chromium_tests_apply_config=[],
                gclient_config='ios',
                gclient_apply_config=[],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'ios',
                },
                testing={
                    'platform': 'mac',
                },
            ),
        'WebRTC Chromium FYI Linux Builder':
            bot_spec.BotSpec.create(
                bot_type=bot_spec.BUILDER,
                chromium_apply_config=['dcheck', 'mb'],
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64
                },
                gclient_apply_config=['webrtc_test_resources'],
                gclient_config='chromium_webrtc_tot',
                set_component_rev={
                    'name': 'src/third_party/webrtc',
                    'rev_str': '%s'
                },
                testing={'platform': 'linux'}),
        'WebRTC Chromium FYI Linux Builder (dbg)':
            bot_spec.BotSpec.create(
                bot_type=bot_spec.BUILDER_TESTER,
                chromium_apply_config=['dcheck', 'mb'],
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64
                },
                gclient_apply_config=[],
                gclient_config='chromium_webrtc_tot',
                set_component_rev={
                    'name': 'src/third_party/webrtc',
                    'rev_str': '%s'
                },
                testing={'platform': 'linux'}),
        'WebRTC Chromium FYI Linux Tester':
            bot_spec.BotSpec.create(
                bot_type=bot_spec.TESTER,
                chromium_apply_config=['dcheck', 'mb'],
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64
                },
                gclient_apply_config=['webrtc_test_resources'],
                gclient_config='chromium_webrtc_tot',
                parent_buildername='WebRTC Chromium FYI Linux Builder',
                set_component_rev={
                    'name': 'src/third_party/webrtc',
                    'rev_str': '%s'
                },
                test_results_config='public_server',
                testing={'platform': 'linux'},
            ),
        'WebRTC Chromium FYI Mac Builder':
            bot_spec.BotSpec.create(
                bot_type=bot_spec.BUILDER,
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
                set_component_rev={
                    'name': 'src/third_party/webrtc',
                    'rev_str': '%s'
                },
                testing={'platform': 'mac'}),
        'WebRTC Chromium FYI Mac Builder (dbg)':
            bot_spec.BotSpec.create(
                bot_type=bot_spec.BUILDER_TESTER,
                chromium_apply_config=[
                    'dcheck',
                    'mb',
                    'mac_toolchain',
                ],
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64
                },
                gclient_apply_config=[],
                gclient_config='chromium_webrtc_tot',
                set_component_rev={
                    'name': 'src/third_party/webrtc',
                    'rev_str': '%s'
                },
                testing={'platform': 'mac'}),
        'WebRTC Chromium FYI Mac Tester':
            bot_spec.BotSpec.create(
                bot_type=bot_spec.TESTER,
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
                parent_buildername='WebRTC Chromium FYI Mac Builder',
                set_component_rev={
                    'name': 'src/third_party/webrtc',
                    'rev_str': '%s'
                },
                test_results_config='public_server',
                testing={'platform': 'mac'},
            ),
        'WebRTC Chromium FYI Win Builder':
            bot_spec.BotSpec.create(
                bot_type=bot_spec.BUILDER,
                chromium_apply_config=['dcheck', 'mb'],
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32
                },
                gclient_apply_config=['webrtc_test_resources'],
                gclient_config='chromium_webrtc_tot',
                set_component_rev={
                    'name': 'src/third_party/webrtc',
                    'rev_str': '%s'
                },
                testing={'platform': 'win'}),
        'WebRTC Chromium FYI Win Builder (dbg)':
            bot_spec.BotSpec.create(
                bot_type=bot_spec.BUILDER_TESTER,
                chromium_apply_config=['dcheck', 'mb'],
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 32
                },
                gclient_apply_config=[],
                gclient_config='chromium_webrtc_tot',
                set_component_rev={
                    'name': 'src/third_party/webrtc',
                    'rev_str': '%s'
                },
                testing={'platform': 'win'}),
        'WebRTC Chromium FYI Win10 Tester':
            bot_spec.BotSpec.create(
                bot_type=bot_spec.TESTER,
                chromium_apply_config=['dcheck', 'mb'],
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32
                },
                gclient_apply_config=['webrtc_test_resources'],
                gclient_config='chromium_webrtc_tot',
                parent_buildername='WebRTC Chromium FYI Win Builder',
                set_component_rev={
                    'name': 'src/third_party/webrtc',
                    'rev_str': '%s'
                },
                test_results_config='public_server',
                testing={'platform': 'win'},
            ),
        'WebRTC Chromium FYI Win7 Tester':
            bot_spec.BotSpec.create(
                bot_type=bot_spec.TESTER,
                chromium_apply_config=['dcheck', 'mb'],
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32
                },
                gclient_apply_config=['webrtc_test_resources'],
                gclient_config='chromium_webrtc_tot',
                parent_buildername='WebRTC Chromium FYI Win Builder',
                set_component_rev={
                    'name': 'src/third_party/webrtc',
                    'rev_str': '%s'
                },
                test_results_config='public_server',
                testing={'platform': 'win'},
            ),
        'WebRTC Chromium FYI Win8 Tester':
            bot_spec.BotSpec.create(
                bot_type=bot_spec.TESTER,
                chromium_apply_config=['dcheck', 'mb'],
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32
                },
                gclient_apply_config=['webrtc_test_resources'],
                gclient_config='chromium_webrtc_tot',
                parent_buildername='WebRTC Chromium FYI Win Builder',
                set_component_rev={
                    'name': 'src/third_party/webrtc',
                    'rev_str': '%s'
                },
                test_results_config='public_server',
                testing={'platform': 'win'},
            ),
    },
}
