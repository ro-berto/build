# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec


def _client_v8_chromium_spec(**kwargs):
  return builder_spec.BuilderSpec.create(
      build_gs_bucket='chromium-v8',
      **kwargs)


SPEC = {
    'Linux - Future':
        _client_v8_chromium_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'Linux - Future (dbg)':
        _client_v8_chromium_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'Linux V8 API Stability':
        _client_v8_chromium_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['v8_canary', 'with_branch_heads'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
}
