# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec

SPEC = {
    'linux-autofill-assistant':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    'linux-blink-web-tests-force-accessibility-rel':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    'linux-layout-tests-edit-ng':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
}
