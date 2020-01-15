# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import bot_spec

SPEC = {
    'settings': {
        'luci_project': 'openscreen',
    },
    'builders': {
        'chromium_linux64_debug':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                gclient_apply_config=['openscreen_tot'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER_TESTER,
                compile_targets=[
                    'chrome/browser/media/router',
                ],
                testing={
                    'platform': 'linux',
                },
            ),
        'chromium_mac_debug':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                gclient_apply_config=['openscreen_tot'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER_TESTER,
                compile_targets=[
                    'chrome/browser/media/router',
                ],
                testing={
                    'platform': 'mac',
                },
            ),
    },
}
