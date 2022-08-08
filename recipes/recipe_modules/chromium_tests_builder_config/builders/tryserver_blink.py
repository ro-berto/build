# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This file is empty but will be used to migrate configs for tryserver.blink src-side.

from .. import builder_spec


SPEC = {
    'win10.20h2-blink-rel':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            build_gs_bucket = "chromium-fyi-archive",   
            simulation_platform='win',
        ),
}