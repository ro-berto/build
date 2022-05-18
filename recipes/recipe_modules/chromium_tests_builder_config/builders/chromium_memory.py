# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec


def _chromium_memory_spec(**kwargs):
  return builder_spec.BuilderSpec.create(
      build_gs_bucket='chromium-memory-archive', **kwargs)

# The config for the following builders is now specified src-side in
# //infra/config/subprojects/chromium/ci/chromium.memory.star
# * Linux ASan LSan Builder
# * Linux ASan LSan Tests (1)
# * Linux ChromiumOS MSan Builder
# * Linux ChromiumOS MSan Tests
# * Linux ASan Tests (sandboxed)
# * WebKit Linux Leak
# * linux-ubsan-vptr
# * win-asan

SPEC = {
    'ios-asan':
        builder_spec.BuilderSpec.create(
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
            cf_archive_build=True,
            cf_gs_bucket='chromium-browser-asan',
            cf_gs_acl='public-read',
            cf_archive_name='ios-asan',
            cf_archive_subdir_suffix='ios-asan',
            simulation_platform='mac',
        ),
    'Linux CFI':
        _chromium_memory_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'Linux MSan Builder':
        _chromium_memory_spec(
            chromium_config='chromium_msan',
            gclient_config='chromium',
            gclient_apply_config=['enable_reclient'],
            chromium_apply_config=['mb'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'Linux MSan Tests':
        _chromium_memory_spec(
            chromium_config='chromium_msan',
            gclient_config='chromium',
            gclient_apply_config=['enable_reclient'],
            chromium_apply_config=['mb'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='Linux MSan Builder',
            simulation_platform='linux',
        ),
    'Linux TSan Builder':
        _chromium_memory_spec(
            chromium_config='chromium_tsan2',
            gclient_config='chromium',
            gclient_apply_config=['enable_reclient'],
            chromium_apply_config=['mb'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    # TODO(crbug.com/1200904): Remove after migration
    'Linux TSan (bionic)':
        _chromium_memory_spec(
            chromium_config='chromium_tsan2',
            gclient_config='chromium',
            chromium_apply_config=['mb'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            execution_mode=builder_spec.COMPILE_AND_TEST,
            simulation_platform='linux',
        ),
    'Linux TSan Tests':
        _chromium_memory_spec(
            chromium_config='chromium_tsan2',
            gclient_config='chromium',
            gclient_apply_config=['enable_reclient'],
            chromium_apply_config=['mb'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='Linux TSan Builder',
            simulation_platform='linux',
        ),
    'Mac ASan 64 Builder':
        _chromium_memory_spec(
            chromium_config='chromium_asan',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            chromium_apply_config=[
                'mb',
            ],
            simulation_platform='mac',
        ),
    'Mac ASan 64 Tests (1)':
        _chromium_memory_spec(
            chromium_config='chromium_asan',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            chromium_apply_config=[
                'mb',
            ],
            execution_mode=builder_spec.TEST,
            parent_buildername='Mac ASan 64 Builder',
            simulation_platform='mac',
        ),
    'Linux Chromium OS ASan LSan Builder':
        _chromium_memory_spec(
            chromium_config='chromium_asan',
            gclient_config='chromium',
            gclient_apply_config=['chromeos'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            chromium_apply_config=['lsan', 'mb'],
            simulation_platform='linux',
        ),
    'Linux Chromium OS ASan LSan Tests (1)':
        _chromium_memory_spec(
            chromium_config='chromium_asan',
            gclient_config='chromium',
            gclient_apply_config=['chromeos'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            chromium_apply_config=['lsan', 'mb'],
            parent_buildername='Linux Chromium OS ASan LSan Builder',
            execution_mode=builder_spec.TEST,
            simulation_platform='linux',
        ),
    'WebKit Linux ASAN':
        _chromium_memory_spec(
            chromium_config='chromium_clang',
            gclient_config='chromium',
            gclient_apply_config=['enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            chromium_apply_config=['asan', 'mb'],
            simulation_platform='linux',
        ),
    'WebKit Linux MSAN':
        _chromium_memory_spec(
            chromium_config='chromium_clang',
            gclient_config='chromium',
            gclient_apply_config=['enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            chromium_apply_config=['asan', 'mb'],
            simulation_platform='linux',
        ),
    'android-asan':
        _chromium_memory_spec(
            android_config='main_builder',
            chromium_config='android_asan',
            chromium_apply_config=['mb'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            gclient_config='chromium',
            gclient_apply_config=['android', 'enable_reclient'],
            simulation_platform='linux',
        ),
}
