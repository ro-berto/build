# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import bot_spec


def _chromium_linux_spec(**kwargs):
  return bot_spec.BotSpec.create(
      build_gs_bucket='chromium-linux-archive', **kwargs)


SPEC = {
    'builders': {
        'fuchsia-arm64-cast':
            _chromium_linux_spec(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['fuchsia_arm64'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'fuchsia',
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'linux',
                },
            ),
        'fuchsia-x64-cast':
            _chromium_linux_spec(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['fuchsia_x64'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'fuchsia',
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'linux',
                },
            ),
        'fuchsia-x64-dbg':
            _chromium_linux_spec(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['fuchsia_x64'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'fuchsia',
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'linux',
                },
            ),
        'linux-gcc-rel':
            _chromium_linux_spec(
                chromium_config='chromium_no_goma',
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
                    'platform': 'linux',
                },
            ),
        'linux-ozone-rel':
            _chromium_linux_spec(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                compile_targets=[],
                testing={
                    'platform': 'linux',
                },
            ),
        'Linux Ozone Tester (X11)':
            _chromium_linux_spec(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='linux-ozone-rel',
                testing={
                    'platform': 'linux',
                },
            ),
        'Linux Ozone Tester (Wayland)':
            _chromium_linux_spec(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='linux-ozone-rel',
                testing={
                    'platform': 'linux',
                },
            ),
        'Linux Builder':
            _chromium_linux_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',

                    # This is specified because 'linux-rel' builder
                    # is one of the slowest builder in CQ (crbug.com/804251).
                    'goma_high_parallel',
                ],
                gclient_config='chromium',
                gclient_apply_config=['use_clang_coverage'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'linux',
                },
            ),
        'linux-trusty-rel':
            _chromium_linux_spec(
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
                testing={
                    'platform': 'linux',
                },
            ),
        'Linux Tests':
            _chromium_linux_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                    'goma_high_parallel',
                ],
                gclient_config='chromium',
                gclient_apply_config=['use_clang_coverage'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='Linux Builder',
                testing={
                    'platform': 'linux',
                },
            ),
        'Linux Builder (dbg)(32)':
            _chromium_linux_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 32,
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'linux',
                },
            ),
        'Linux Builder (dbg)':
            _chromium_linux_spec(
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
                    'platform': 'linux',
                },
            ),
        'Linux Tests (dbg)(1)':
            _chromium_linux_spec(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='Linux Builder (dbg)',
                testing={
                    'platform': 'linux',
                },
            ),
        'Cast Audio Linux':
            _chromium_linux_spec(
                chromium_config='chromium_clang',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                testing={
                    'platform': 'linux',
                },
            ),
        'Cast Linux':
            _chromium_linux_spec(
                chromium_config='chromium_clang',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                testing={
                    'platform': 'linux',
                },
            ),
        'Fuchsia ARM64 Cast Audio':
            _chromium_linux_spec(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['fuchsia_arm64'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'fuchsia',
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'linux',
                },
            ),
        'Fuchsia ARM64':
            _chromium_linux_spec(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['fuchsia_arm64', 'fuchsia_arm64_host'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'fuchsia',
                },
                bot_type=bot_spec.BUILDER_TESTER,
                # TODO(crbug.com/1031210): use parallel test after bots added.
                # Swarming bots will be added to the arm64 servers after the
                # SSD upgrades.
                serialize_tests=True,
                testing={
                    'platform': 'linux',
                },
            ),
        'Fuchsia x64 Cast Audio':
            _chromium_linux_spec(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['fuchsia_x64'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'fuchsia',
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'linux',
                },
            ),
        'Fuchsia x64':
            _chromium_linux_spec(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['fuchsia_x64'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'fuchsia',
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'linux',
                },
            ),
        'Leak Detection Linux':
            _chromium_linux_spec(
                chromium_config='chromium',
                gclient_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                chromium_tests_apply_config=['staging'],
                test_results_config='staging_server',
                testing={
                    'platform': 'linux',
                },
            ),
        'Network Service Linux':
            _chromium_linux_spec(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER_TESTER,
                testing={
                    'platform': 'linux',
                },
            ),
    },
}
