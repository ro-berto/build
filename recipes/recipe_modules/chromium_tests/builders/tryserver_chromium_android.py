# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_spec

SPEC = {
    'android-opus-arm-rel':
        bot_spec.BotSpec.create(
            chromium_config='android',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            simulation_platform='linux',
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
        ),
    'android_blink_rel':
        bot_spec.BotSpec.create(
            android_config='main_builder',
            chromium_apply_config=[
                'mb',
            ],
            isolate_server='https://isolateserver.appspot.com',
            chromium_config='android',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            gclient_config='chromium',
            gclient_apply_config=['android'],
            simulation_platform='linux',
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
        ),
}
