# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_spec

SPEC = {
    'android-lollipop-arm-rel-swarming':
        bot_spec.BotSpec.create(
            chromium_config='android',
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
            },
            android_config='main_builder_mb',
            simulation_platform='linux',
        ),
    'android-marshmallow-arm64-rel-swarming':
        bot_spec.BotSpec.create(
            chromium_config='android',
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
            },
            android_config='main_builder_mb',
            simulation_platform='linux',
        ),
    'linux-rel-swarming':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
            },
            simulation_platform='linux',
        ),
    'mac-rel-swarming':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
            },
            simulation_platform='mac',
        ),
    'win-rel-swarming':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
            },
            simulation_platform='win',
        ),
}

# Use the same config for builders using staging swarming instance.
_CHROMIUM_SWARM_STAGING = 'https://chromium-swarm-staging.appspot.com'

SPEC['linux-rel-swarming-staging'] = (
    SPEC['linux-rel-swarming'].evolve(swarming_server=_CHROMIUM_SWARM_STAGING))

SPEC['win-rel-swarming-staging'] = (
    SPEC['win-rel-swarming'].evolve(swarming_server=_CHROMIUM_SWARM_STAGING))
