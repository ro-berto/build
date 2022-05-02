# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec

# The config for the following builders is now specified src-side in
# //infra/config/subprojects/chromium/ci/chromium.mac.star
# * Mac Builder
# * Mac Builder (dbg)
# * Mac10.11 Tests
# * Mac10.12 Tests
# * Mac10.13 Tests
# * Mac10.14 Tests
# * Mac10.15 Tests
# * Mac11 Tests
# * Mac11 Tests (dbg)
# * ios-catalyst
# * ios-device
# * ios-simulator
# * ios-simulator-full-configs
# * ios-simulator-noncq
# * mac-arm64-rel
# * mac11-arm64-rel-tests

SPEC = {
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
}
