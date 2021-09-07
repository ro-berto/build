# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec

SPEC = {
    'Mojo Android':
        builder_spec.BuilderSpec.create(
            chromium_config='android',
            chromium_apply_config=['android'],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='arm64_builder_mb',
            simulation_platform='linux',
        ),
    'Mojo ChromiumOS':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['chromeos'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_PLATFORM': 'linux',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'Mojo Linux':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'mac-mojo-rel':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='mac',
        ),
    'Mojo Windows':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_PLATFORM': 'win',
                'TARGET_BITS': 32,
            },
            simulation_platform='win',
        ),
}
