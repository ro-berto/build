# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec


def _chromium_linux_spec(**kwargs):
  return builder_spec.BuilderSpec.create(
      build_gs_bucket='chromium-linux-archive', **kwargs)

# The config for the following builders is now specified src-side in
# //infra/config/subprojects/chromium/ci/chromium.linux.star
# * Linux Builder
# * Linux Builder (dbg)
# * Linux Tests
# * Linux Tests (dbg)(1)

SPEC = {
    'fuchsia-arm64-cast':
        _chromium_linux_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['fuchsia_arm64'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'fuchsia',
            },
            simulation_platform='linux',
        ),
    'fuchsia-x64-cast':
        _chromium_linux_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['fuchsia_x64'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'fuchsia',
            },
            simulation_platform='linux',
        ),
    'fuchsia-x64-dbg':
        _chromium_linux_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['fuchsia_x64', 'enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'fuchsia',
            },
            simulation_platform='linux',
        ),
    'linux-bfcache-rel':
        _chromium_linux_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            gclient_apply_config=['enable_reclient'],
            simulation_platform='linux',
        ),
    'linux-extended-tracing-rel':
        _chromium_linux_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            gclient_apply_config=['enable_reclient'],
            simulation_platform='linux',
        ),
    'linux-gcc-rel':
        _chromium_linux_spec(
            chromium_config='chromium_no_goma',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'enable_reclient',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'linux-no-base-tracing-rel':
        _chromium_linux_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'Linux Builder (Wayland)':
        _chromium_linux_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'use_clang_coverage',
                'enable_reclient',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'Linux Tests (Wayland)':
        _chromium_linux_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'use_clang_coverage',
                'enable_reclient',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='Linux Builder (Wayland)',
            simulation_platform='linux',
        ),
    'Cast Audio Linux':
        _chromium_linux_spec(
            chromium_config='chromium_clang',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'Cast Linux':
        _chromium_linux_spec(
            chromium_config='chromium_clang',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'Cast Linux Debug':
        _chromium_linux_spec(
            chromium_config='chromium_clang',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'Cast Linux ARM64':
        _chromium_linux_spec(
            chromium_config='chromium_clang',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['arm64', 'enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'Fuchsia ARM64 Cast Audio':
        _chromium_linux_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['fuchsia_arm64'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'fuchsia',
            },
            simulation_platform='linux',
        ),
    'Fuchsia ARM64':
        _chromium_linux_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['fuchsia_arm64', 'fuchsia_arm64_host'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'fuchsia',
            },
            simulation_platform='linux',
        ),
    'Fuchsia x64 Cast Audio':
        _chromium_linux_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['fuchsia_x64'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'fuchsia',
            },
            simulation_platform='linux',
        ),
    'Fuchsia x64':
        _chromium_linux_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['fuchsia_x64'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'fuchsia',
            },
            simulation_platform='linux',
        ),
    'Leak Detection Linux':
        _chromium_linux_spec(
            chromium_config='chromium',
            gclient_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            gclient_apply_config=['enable_reclient'],
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    'Network Service Linux':
        _chromium_linux_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            gclient_apply_config=['enable_reclient'],
            simulation_platform='linux',
        ),
}
