# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_spec

COMMON_BOT_CONFIG = bot_spec.BotSpec.create(
    chromium_config='chromium',
    chromium_apply_config=['mb', 'mb_luci_auth'],
    gclient_config='chromium',
    chromium_config_kwargs={
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
    },
    tests=[],
    test_results_config='public_server',
    testing={
        'platform': 'linux',
    },
)

SPEC = {
    'builders': {
        'devtools_frontend_linux_blink_light_rel': COMMON_BOT_CONFIG,
        'devtools_frontend_linux_blink_rel': COMMON_BOT_CONFIG,
    },
}
