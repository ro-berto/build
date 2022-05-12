# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec

# The config for the following builders is now specified src-side in
# //infra/config/subprojects/chromium/ci/chromium.star
# * android-archive-dbg
# * android-archive-rel
# * linux-archive-dbg
# * linux-archive-rel
# * mac-arm64-archive-dbg
# * mac-arm64-archive-rel
# * mac-official
# * win-archive-rel
# * win-official
# * win32-archive-rel
# * win32-official

SPEC = {
    'win32-archive-dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'clobber',
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
            },
            simulation_platform='win',
        ),
    'win-archive-dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'clobber',
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            simulation_platform='win',
        ),
    'mac-archive-dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'clobber',
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            simulation_platform='mac',
        ),
    'mac-archive-rel':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'clobber',
                'mb',
                'goma_use_local',  # to mitigate compile step timeout (crbug.com/1056935).
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='mac',
        ),
    'fuchsia-official':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=['fuchsia_x64'],
            chromium_config_kwargs={
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'fuchsia',
            },
            simulation_platform='linux',
        ),
    'linux-official':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=['checkout_pgo_profiles', 'enable_reclient'],
            chromium_config_kwargs={
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'android-official':
        builder_spec.BuilderSpec.create(
            chromium_config='android',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=['android', 'enable_reclient'],
            chromium_config_kwargs={
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
            },
            android_config='main_builder',
            simulation_platform='linux',
        ),
}
