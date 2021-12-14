# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec

SPEC = {
    'android-lollipop-arm-rel-swarming':
        builder_spec.BuilderSpec.create(
            chromium_config='android',
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
        builder_spec.BuilderSpec.create(
            chromium_config='android',
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
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
            },
            simulation_platform='linux',
        ),
    'linux-ssd-rel-swarming':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
            },
            simulation_platform='linux',
        ),
    'mac-rel-swarming':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
            },
            simulation_platform='mac',
        ),
    'mac-arm-rel-swarming':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
            },
            simulation_platform='mac',
        ),
    'win11-rel-swarming':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
            },
            simulation_platform='win',
        ),
    'win-rel-swarming':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
            },
            simulation_platform='win',
        ),
}

# Use the same config for builders using staging swarming instance.
SPEC['linux-rel-swarming-staging'] = SPEC['linux-rel-swarming']
SPEC['win-rel-swarming-staging'] = SPEC['win-rel-swarming']
