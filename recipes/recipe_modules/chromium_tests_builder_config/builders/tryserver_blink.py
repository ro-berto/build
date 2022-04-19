# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec

SPEC = {
    'linux-blink-rel':
        builder_spec.BuilderSpec.create(
            gclient_config='chromium',
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
}
