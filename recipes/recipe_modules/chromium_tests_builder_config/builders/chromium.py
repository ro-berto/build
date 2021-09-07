# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec

SPEC = {
    'win32-official':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=['checkout_pgo_profiles'],
            chromium_config_kwargs={
                'TARGET_BITS': 32,
            },
            simulation_platform='win',
        ),
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
    'win32-archive-rel':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'clobber',
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            archive_build=True,
            gs_bucket='chromium-browser-snapshots',
            gs_build_name='Win',
            gs_acl='public-read',
            simulation_platform='win',
        ),
    'win-official':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=['checkout_pgo_profiles'],
            chromium_config_kwargs={
                'TARGET_BITS': 64,
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
    'win-archive-rel':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'clobber',
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            archive_build=True,
            gs_bucket='chromium-browser-snapshots',
            gs_build_name='Win_x64',
            gs_acl='public-read',
            simulation_platform='win',
        ),
    'mac-official':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=['checkout_pgo_profiles'],
            chromium_config_kwargs={
                'TARGET_BITS': 64,
            },
            simulation_platform='mac',
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
            archive_build=True,
            gs_bucket='chromium-browser-snapshots',
            gs_build_name='Mac',
            gs_acl='public-read',
            simulation_platform='mac',
        ),
    'mac-arm64-archive-dbg':
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
    'mac-arm64-archive-rel':
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
            archive_build=True,
            gs_bucket='chromium-browser-snapshots',
            gs_build_name='Mac_Arm',
            gs_acl='public-read',
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
            gclient_apply_config=['checkout_pgo_profiles'],
            chromium_config_kwargs={
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'linux-archive-dbg':
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
            simulation_platform='linux',
        ),
    'linux-archive-rel':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'clobber',
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            archive_build=True,
            gs_bucket='chromium-browser-snapshots',
            gs_build_name='Linux_x64',
            gs_acl='public-read',
            simulation_platform='linux',
        ),
    'android-official':
        builder_spec.BuilderSpec.create(
            chromium_config='android',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
            },
            android_config='main_builder',
            simulation_platform='linux',
        ),
    'android-archive-dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='android',
            chromium_apply_config=[
                'clobber',
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
            },
            android_config='main_builder',
            simulation_platform='linux',
        ),
    'android-archive-rel':
        builder_spec.BuilderSpec.create(
            chromium_config='android',
            chromium_apply_config=[
                'clobber',
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
            },
            android_config='main_builder',
            archive_build=True,
            gs_bucket='chromium-browser-snapshots',
            gs_build_name='Android',
            gs_acl='public-read',
            simulation_platform='linux',
        ),
}
