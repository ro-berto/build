# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import bot_spec

SPEC = {
    'builders': {
        'android-opus-kitkat-arm-rel':
            bot_spec.BotSpec.create(
                chromium_config='android',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                gclient_apply_config=['android'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                    'TARGET_PLATFORM': 'android',
                },
                android_config='main_builder',
                bot_type=bot_spec.BUILDER_TESTER,
                testing={
                    'platform': 'linux',
                },
            ),
        'android_blink_rel':
            bot_spec.BotSpec.create(
                android_config='main_builder',
                chromium_apply_config=[
                    'mb',
                ],
                chromium_config='android',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                    'TARGET_PLATFORM': 'android',
                },
                gclient_config='chromium',
                gclient_apply_config=['android'],
                bot_type=bot_spec.BUILDER_TESTER,
                testing={
                    'platform': 'linux',
                },
            ),
    },
}
