# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec


def _chromium_mac_spec(**kwargs):
  return builder_spec.BuilderSpec.create(
      build_gs_bucket='chromium-mac-archive', **kwargs)

# The config for the following builders is now specified src-side in
# //infra/config/subprojects/chromium/ci/chromium.mac.star
# * Mac Builder
# * Mac10.11 Tests
# * Mac10.12 Tests
# * Mac10.13 Tests
# * Mac10.14 Tests
# * Mac10.15 Tests
# * Mac11 Tests
# * ios-simulator
# * ios-simulator-full-configs
# * ios-simulator-noncq
# * mac-arm64-rel
# * mac11-arm64-rel-tests

SPEC = {
    'ios-catalyst':
        _chromium_mac_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            gclient_config='ios',
            gclient_apply_config=[],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
                'HOST_PLATFORM': 'mac',
            },
            simulation_platform='mac',
        ),
    'ios-device':
        _chromium_mac_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            gclient_config='ios',
            gclient_apply_config=[],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
                'HOST_PLATFORM': 'mac',
            },
            simulation_platform='mac',
        ),
    'mac-arm64-on-arm64-rel':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            },
            simulation_platform='mac',
        ),
    'Mac11 Tests (dbg)':
        _chromium_mac_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'mac',
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='Mac Builder (dbg)',
            simulation_platform='linux',
        ),
    'Mac Builder (dbg)':
        _chromium_mac_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'mac',
            },
            simulation_platform='mac',
        ),
}
