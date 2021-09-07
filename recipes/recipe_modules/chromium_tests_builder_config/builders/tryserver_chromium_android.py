# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec

SPEC = {
    'android-opus-arm-rel':
        builder_spec.BuilderSpec.create(
            chromium_config='android',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            simulation_platform='linux',
        ),
    'android_blink_rel':
        builder_spec.BuilderSpec.create(
            android_config='main_builder',
            chromium_apply_config=[
                'mb',
            ],
            chromium_config='android',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            gclient_config='chromium',
            gclient_apply_config=['android'],
            simulation_platform='linux',
        ),
}
