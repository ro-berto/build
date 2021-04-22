# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec

COMMON_BOT_CONFIG = builder_spec.BuilderSpec.create(
    chromium_config='chromium',
    chromium_apply_config=['mb'],
    isolate_server='https://isolateserver.appspot.com',
    gclient_config='chromium',
    chromium_config_kwargs={
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
    },
    test_results_config='public_server',
    simulation_platform='linux',
    isolate_use_cas=True,
)

SPEC = {
    'devtools_frontend_linux_blink_light_rel': COMMON_BOT_CONFIG,
    'devtools_frontend_linux_blink_rel': COMMON_BOT_CONFIG,
}
