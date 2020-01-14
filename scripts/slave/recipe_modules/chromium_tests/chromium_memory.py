# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import bot_spec

SPEC = {
    'settings': {
        'build_gs_bucket': 'chromium-memory-archive',
    },
    'builders': {
        'Android CFI':
            bot_spec.BotSpec.create(
                chromium_config='android',
                chromium_apply_config=['mb', 'download_vr_test_apks'],
                gclient_config='chromium',
                gclient_apply_config=['android'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                    'TARGET_PLATFORM': 'android',
                },
                android_config='main_builder',
                bot_type=bot_spec.BUILDER_TESTER,
                testing={'platform': 'linux'},
            ),
        'Linux ASan LSan Builder':
            bot_spec.BotSpec.create(
                chromium_config='chromium_asan',
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                # This doesn't affect the build, but ensures that trybots get
                # the right runtime flags.
                chromium_apply_config=['lsan', 'mb', 'goma_high_parallel'],
                bot_type=bot_spec.BUILDER,
                testing={'platform': 'linux'},
            ),
        'Linux ASan LSan Tests (1)':
            bot_spec.BotSpec.create(
                chromium_config='chromium_asan',
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                # Enable LSan at runtime. This disables the sandbox in browser
                # tests. http://crbug.com/336218
                chromium_apply_config=['lsan', 'mb', 'goma_high_parallel'],
                bot_type=bot_spec.TESTER,
                parent_buildername='Linux ASan LSan Builder',
                testing={'platform': 'linux'},
            ),
        'Linux ASan Tests (sandboxed)':
            bot_spec.BotSpec.create(
                chromium_config='chromium_asan',
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                chromium_apply_config=['mb', 'goma_high_parallel'],
                # We want to test ASan+sandbox as well, so run browser tests
                # again, this time with LSan disabled.
                bot_type=bot_spec.TESTER,
                parent_buildername='Linux ASan LSan Builder',
                testing={'platform': 'linux'},
            ),
        'Linux CFI':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER_TESTER,
                testing={'platform': 'linux'},
            ),
        'Linux MSan Builder':
            bot_spec.BotSpec.create(
                chromium_config='chromium_msan',
                gclient_config='chromium',
                chromium_apply_config=['mb'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                testing={'platform': 'linux'},
            ),
        'Linux MSan Tests':
            bot_spec.BotSpec.create(
                chromium_config='chromium_msan',
                gclient_config='chromium',
                chromium_apply_config=['mb'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='Linux MSan Builder',
                testing={'platform': 'linux'},
            ),
        'Linux ChromiumOS MSan Builder':
            bot_spec.BotSpec.create(
                chromium_config='chromium_msan',
                gclient_config='chromium',
                gclient_apply_config=['chromeos'],
                chromium_apply_config=['mb'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                testing={'platform': 'linux'},
            ),
        'Linux ChromiumOS MSan Tests':
            bot_spec.BotSpec.create(
                chromium_config='chromium_msan',
                gclient_config='chromium',
                gclient_apply_config=['chromeos'],
                chromium_apply_config=['mb'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='Linux ChromiumOS MSan Builder',
                testing={'platform': 'linux'},
            ),
        'Linux TSan Builder':
            bot_spec.BotSpec.create(
                chromium_config='chromium_tsan2',
                gclient_config='chromium',
                chromium_apply_config=['mb'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'linux',
                },
            ),
        'Linux TSan Tests':
            bot_spec.BotSpec.create(
                chromium_config='chromium_tsan2',
                gclient_config='chromium',
                chromium_apply_config=['mb'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='Linux TSan Builder',
                testing={
                    'platform': 'linux',
                },
            ),
        'Mac ASan 64 Builder':
            bot_spec.BotSpec.create(
                chromium_config='chromium_asan',
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                chromium_apply_config=[
                    'mb',
                ],
                bot_type=bot_spec.BUILDER,
                testing={'platform': 'mac'},
            ),
        'Mac ASan 64 Tests (1)':
            bot_spec.BotSpec.create(
                chromium_config='chromium_asan',
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                chromium_apply_config=[
                    'mb',
                ],
                bot_type=bot_spec.TESTER,
                parent_buildername='Mac ASan 64 Builder',
                testing={'platform': 'mac'},
            ),
        'Linux Chromium OS ASan LSan Builder':
            bot_spec.BotSpec.create(
                chromium_config='chromium_asan',
                gclient_config='chromium',
                gclient_apply_config=['chromeos'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                chromium_apply_config=['lsan', 'mb'],
                bot_type=bot_spec.BUILDER,
                testing={'platform': 'linux'},
            ),
        'Linux Chromium OS ASan LSan Tests (1)':
            bot_spec.BotSpec.create(
                chromium_config='chromium_asan',
                gclient_config='chromium',
                gclient_apply_config=['chromeos'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                chromium_apply_config=['lsan', 'mb'],
                parent_buildername='Linux Chromium OS ASan LSan Builder',
                bot_type=bot_spec.TESTER,
                testing={'platform': 'linux'},
            ),
        'WebKit Linux ASAN':
            bot_spec.BotSpec.create(
                chromium_config='chromium_clang',
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                chromium_apply_config=['asan', 'mb'],
                tests=[],
                testing={'platform': 'linux'},
            ),
        'WebKit Linux MSAN':
            bot_spec.BotSpec.create(
                chromium_config='chromium_clang',
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                chromium_apply_config=['asan', 'mb'],
                tests=[],
                testing={'platform': 'linux'},
            ),
        'WebKit Linux Leak':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                chromium_apply_config=['mb'],
                compile_targets=[
                    'blink_tests',
                ],
                tests=[],
                testing={'platform': 'linux'},
            ),
        'android-asan':
            bot_spec.BotSpec.create(
                android_config='main_builder',
                chromium_config='android_asan',
                chromium_apply_config=['mb'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'android',
                },
                gclient_config='chromium',
                gclient_apply_config=['android'],
                bot_type=bot_spec.BUILDER_TESTER,
                testing={'platform': 'linux'},
            ),
        'win-asan':
            bot_spec.BotSpec.create(
                chromium_config='chromium_win_clang_asan',
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                chromium_apply_config=['mb'],
                bot_type=bot_spec.BUILDER_TESTER,
                testing={'platform': 'win'},
            ),
    },
}
