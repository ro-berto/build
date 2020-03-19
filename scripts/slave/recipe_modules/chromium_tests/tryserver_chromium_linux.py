# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import bot_spec

SPEC = {
    'builders': {
        'linux-layout-tests-fragment-item':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                tests=[],
                test_results_config='staging_server',
                testing={
                    'platform': 'linux',
                },
            ),
        'linux-layout-tests-fragment-paint':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                test_results_config='staging_server',
                testing={
                    'platform': 'linux',
                },
            ),
    },
}
