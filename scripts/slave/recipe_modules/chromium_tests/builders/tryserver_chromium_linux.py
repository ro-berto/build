# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_spec

SPEC = {
    'linux-autofill-assistant':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    'linux-layout-tests-edit-ng':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    'linux-layout-tests-fragment-item':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
}
