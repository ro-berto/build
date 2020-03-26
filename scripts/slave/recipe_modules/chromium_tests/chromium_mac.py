# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import bot_spec

SPEC = {
    'settings': {
        'build_gs_bucket': 'chromium-mac-archive',
    },
    'builders': {
        'ios-device':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                    'mac_toolchain',
                ],
                chromium_tests_apply_config=[],
                gclient_config='ios',
                gclient_apply_config=[],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'ios',
                    'HOST_PLATFORM': 'mac',
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'mac',
                },
            ),
        'ios-simulator-full-configs':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                    'mac_toolchain',
                ],
                chromium_tests_apply_config=[],
                gclient_config='ios',
                gclient_apply_config=[],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'ios',
                    'HOST_PLATFORM': 'mac',
                },
                testing={
                    'platform': 'mac',
                },
            ),
        'ios-simulator-noncq':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                    'mac_toolchain',
                ],
                chromium_tests_apply_config=[],
                gclient_config='ios',
                gclient_apply_config=[],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'ios',
                    'HOST_PLATFORM': 'mac',
                },
                testing={
                    'platform': 'mac',
                },
            ),
        'ios-simulator':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                    'mac_toolchain',
                ],
                chromium_tests_apply_config=[],
                gclient_config='ios',
                gclient_apply_config=[],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'ios',
                    'HOST_PLATFORM': 'mac',
                },
                testing={
                    'platform': 'mac',
                },
            ),
        'Mac Builder':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'mac',
                },
            ),
        'Mac Builder Code Coverage':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                gclient_apply_config=['use_clang_coverage'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'mac',
                },
            ),
        'Mac10.10 Tests':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='Mac Builder',
                testing={
                    'platform': 'mac',
                },
            ),
        'Mac10.11 Tests':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='Mac Builder',
                testing={
                    'platform': 'mac',
                },
            ),
        'Mac10.12 Tests':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='Mac Builder',
                testing={
                    'platform': 'mac',
                },
            ),
        'Mac10.13 Tests':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='Mac Builder',
                testing={
                    'platform': 'mac',
                },
            ),
        'Mac10.13 Tests Code Coverage':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                gclient_apply_config=['use_clang_coverage'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='Mac Builder Code Coverage',
                testing={
                    'platform': 'mac',
                },
            ),
        'Mac10.14 Tests':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='Mac Builder',
                testing={
                    'platform': 'mac',
                },
            ),
        'Mac Builder (dbg)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'mac',
                },
            ),
        'Mac10.13 Tests (dbg)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='Mac Builder (dbg)',
                testing={
                    'platform': 'mac',
                },
            ),
        'WebKit Mac10.13 (retina)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='Mac Builder',
                testing={
                    'platform': 'mac',
                },
            ),
        'mac-upload-perfetto':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER_TESTER,
                testing={
                    'platform': 'mac',
                },
            ),
    },
}
