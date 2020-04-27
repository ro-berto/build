# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_spec

RESULTS_URL = 'https://chromeperf.appspot.com'


def _chromium_android_fyi_spec(**kwargs):
  return bot_spec.BotSpec.create(
      build_gs_bucket='chromium-android-archive', **kwargs)


SPEC = {
    'Android WebView P Blink-CORS FYI (rel)':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'Android WebLayer P FYI (rel)':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'Android WebView P FYI (rel)':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'Memory Infra Tester':
        _chromium_android_fyi_spec(
            chromium_config='android',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            bot_type=bot_spec.BUILDER_TESTER,
            android_config='main_builder_mb',
            simulation_platform='linux',
        ),
    'android-marshmallow-x86-fyi-rel':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='x86_builder',
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'android-pie-arm64-fyi-rel':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'android-pie-x86-fyi-rel':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='x86_builder',
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'android-weblayer-pie-x86-fyi-rel':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='x86_builder',
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'android-bfcache-rel':
        _chromium_android_fyi_spec(
            chromium_config='android',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder_mb',
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
}
