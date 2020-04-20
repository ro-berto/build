# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_spec


def _chromium_memory_spec(**kwargs):
  return bot_spec.BotSpec.create(
      build_gs_bucket='chromium-memory-archive', **kwargs)


SPEC = {
    'Android CFI':
        _chromium_memory_spec(
            chromium_config='android',
            chromium_apply_config=[
                'mb', 'mb_luci_auth', 'download_vr_test_apks'
            ],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'Linux ASan LSan Builder':
        _chromium_memory_spec(
            chromium_config='chromium_asan',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            # This doesn't affect the build, but ensures that trybots get
            # the right runtime flags.
            chromium_apply_config=[
                'lsan', 'mb', 'mb_luci_auth', 'goma_high_parallel'
            ],
            bot_type=bot_spec.BUILDER,
            simulation_platform='linux',
        ),
    'Linux ASan LSan Tests (1)':
        _chromium_memory_spec(
            chromium_config='chromium_asan',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            # Enable LSan at runtime. This disables the sandbox in browser
            # tests. http://crbug.com/336218
            chromium_apply_config=[
                'lsan', 'mb', 'mb_luci_auth', 'goma_high_parallel'
            ],
            bot_type=bot_spec.TESTER,
            parent_buildername='Linux ASan LSan Builder',
            simulation_platform='linux',
        ),
    'Linux ASan Tests (sandboxed)':
        _chromium_memory_spec(
            chromium_config='chromium_asan',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            chromium_apply_config=['mb', 'mb_luci_auth', 'goma_high_parallel'],
            # We want to test ASan+sandbox as well, so run browser tests
            # again, this time with LSan disabled.
            bot_type=bot_spec.TESTER,
            parent_buildername='Linux ASan LSan Builder',
            simulation_platform='linux',
        ),
    'Linux CFI':
        _chromium_memory_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'Linux MSan Builder':
        _chromium_memory_spec(
            chromium_config='chromium_msan',
            gclient_config='chromium',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.BUILDER,
            simulation_platform='linux',
        ),
    'Linux MSan Tests':
        _chromium_memory_spec(
            chromium_config='chromium_msan',
            gclient_config='chromium',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.TESTER,
            parent_buildername='Linux MSan Builder',
            simulation_platform='linux',
        ),
    'Linux ChromiumOS MSan Builder':
        _chromium_memory_spec(
            chromium_config='chromium_msan',
            gclient_config='chromium',
            gclient_apply_config=['chromeos'],
            chromium_apply_config=['mb', 'mb_luci_auth'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.BUILDER,
            simulation_platform='linux',
        ),
    'Linux ChromiumOS MSan Tests':
        _chromium_memory_spec(
            chromium_config='chromium_msan',
            gclient_config='chromium',
            gclient_apply_config=['chromeos'],
            chromium_apply_config=['mb', 'mb_luci_auth'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.TESTER,
            parent_buildername='Linux ChromiumOS MSan Builder',
            simulation_platform='linux',
        ),
    'Linux TSan Builder':
        _chromium_memory_spec(
            chromium_config='chromium_tsan2',
            gclient_config='chromium',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.BUILDER,
            simulation_platform='linux',
        ),
    'Linux TSan Tests':
        _chromium_memory_spec(
            chromium_config='chromium_tsan2',
            gclient_config='chromium',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.TESTER,
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
                'mb_luci_auth',
            ],
            bot_type=bot_spec.BUILDER,
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
                'mb_luci_auth',
            ],
            bot_type=bot_spec.TESTER,
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
            chromium_apply_config=['lsan', 'mb', 'mb_luci_auth'],
            bot_type=bot_spec.BUILDER,
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
            chromium_apply_config=['lsan', 'mb', 'mb_luci_auth'],
            parent_buildername='Linux Chromium OS ASan LSan Builder',
            bot_type=bot_spec.TESTER,
            simulation_platform='linux',
        ),
    'WebKit Linux ASAN':
        _chromium_memory_spec(
            chromium_config='chromium_clang',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            chromium_apply_config=['asan', 'mb', 'mb_luci_auth'],
            tests=[],
            simulation_platform='linux',
        ),
    'WebKit Linux MSAN':
        _chromium_memory_spec(
            chromium_config='chromium_clang',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            chromium_apply_config=['asan', 'mb', 'mb_luci_auth'],
            tests=[],
            simulation_platform='linux',
        ),
    'WebKit Linux Leak':
        _chromium_memory_spec(
            chromium_config='chromium',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            chromium_apply_config=['mb', 'mb_luci_auth'],
            compile_targets=[
                'blink_tests',
            ],
            tests=[],
            simulation_platform='linux',
        ),
    'android-asan':
        _chromium_memory_spec(
            android_config='main_builder',
            chromium_config='android_asan',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            gclient_config='chromium',
            gclient_apply_config=['android'],
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'win-asan':
        _chromium_memory_spec(
            chromium_config='chromium_win_clang_asan',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            chromium_apply_config=['mb', 'mb_luci_auth'],
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='win',
        ),
}
