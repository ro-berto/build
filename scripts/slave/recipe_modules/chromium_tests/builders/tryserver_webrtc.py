# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_spec


def _tryserver_webrtc_spec(**kwargs):
  return bot_spec.BotSpec.create(luci_project='webrtc', **kwargs)


SPEC = {
    'builders': {
        'android_chromium_compile':
            _tryserver_webrtc_spec(
                android_config='base_config',
                bot_type=bot_spec.BUILDER,
                chromium_apply_config=[
                    'dcheck', 'mb', 'mb_luci_auth', 'android'
                ],
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'android'
                },
                gclient_apply_config=['android'],
                gclient_config='chromium_no_telemetry_dependencies',
                testing={'platform': 'linux'}),
        'linux_chromium_compile':
            _tryserver_webrtc_spec(
                bot_type=bot_spec.BUILDER,
                chromium_apply_config=['dcheck', 'mb', 'mb_luci_auth'],
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64
                },
                gclient_apply_config=[],
                gclient_config='chromium_no_telemetry_dependencies',
                testing={'platform': 'linux'}),
        'linux_chromium_compile_dbg':
            _tryserver_webrtc_spec(
                bot_type=bot_spec.BUILDER,
                chromium_apply_config=['dcheck', 'mb', 'mb_luci_auth'],
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64
                },
                gclient_apply_config=[],
                gclient_config='chromium_no_telemetry_dependencies',
                testing={'platform': 'linux'}),
        'mac_chromium_compile':
            _tryserver_webrtc_spec(
                bot_type=bot_spec.BUILDER,
                chromium_apply_config=['dcheck', 'mb', 'mb_luci_auth'],
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64
                },
                gclient_apply_config=[],
                gclient_config='chromium_no_telemetry_dependencies',
                testing={'platform': 'mac'}),
        'win_chromium_compile':
            _tryserver_webrtc_spec(
                bot_type=bot_spec.BUILDER,
                chromium_apply_config=['dcheck', 'mb', 'mb_luci_auth'],
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64
                },
                gclient_apply_config=[],
                gclient_config='chromium_no_telemetry_dependencies',
                testing={'platform': 'win'}),
        'win_chromium_compile_dbg':
            _tryserver_webrtc_spec(
                bot_type=bot_spec.BUILDER,
                chromium_apply_config=['dcheck', 'mb', 'mb_luci_auth'],
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64
                },
                gclient_apply_config=[],
                gclient_config='chromium_no_telemetry_dependencies',
                testing={'platform': 'win'}),
    },
}
