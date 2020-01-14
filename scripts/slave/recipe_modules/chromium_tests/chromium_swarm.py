# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import bot_spec

SPEC = {
    'builders': {
        'android-kitkat-arm-rel':
            bot_spec.BotSpec.create(
                chromium_config='android',
                gclient_config='chromium',
                gclient_apply_config=['android'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'arm',
                },
                android_config='main_builder_mb',
                testing={
                    'platform': 'linux',
                },
                bot_type=bot_spec.BUILDER_TESTER,
            ),
        'android-marshmallow-arm64-rel':
            bot_spec.BotSpec.create(
                chromium_config='android',
                gclient_config='chromium',
                gclient_apply_config=['android'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'arm',
                },
                android_config='main_builder_mb',
                testing={
                    'platform': 'linux',
                },
                bot_type=bot_spec.BUILDER_TESTER,
            ),
        'linux-rel':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                },
                testing={
                    'platform': 'linux',
                },
                bot_type=bot_spec.BUILDER_TESTER,
            ),
        'mac-rel':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                },
                testing={
                    'platform': 'mac',
                },
                bot_type=bot_spec.BUILDER_TESTER,
            ),
        'win-rel':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                },
                testing={
                    'platform': 'win',
                },
                bot_type=bot_spec.BUILDER_TESTER,
            ),
    },
}

# TODO(crbug.com/955013): remove this when rename finished.
_builders = SPEC['builders']
_builders['Android N5 Swarm'] = _builders['android-kitkat-arm-rel']
_builders['Android N5X Swarm'] = _builders['android-marshmallow-arm64-rel']
_builders['Linux Swarm'] = _builders['linux-rel']
_builders['Windows Swarm'] = _builders['win-rel']
_builders['Mac Swarm'] = _builders['mac-rel']
