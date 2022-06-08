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
# * Linux ASan Tests (sandboxed)
# * Linux CFI
# * Linux Chromium OS ASan LSan Builder
# * Linux Chromium OS ASan LSan Tests (1)
# * Linux ChromiumOS MSan Builder
# * Linux ChromiumOS MSan Tests
# * Linux MSan Builder
# * Linux MSan Tests
# * Linux TSan Builder
# * Linux TSan Tests
# * Mac ASan 64 Builder
# * Mac ASan 64 Tests (1)
# * WebKit Linux ASAN
# * WebKit Linux Leak
# * WebKit Linux MSAN
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
