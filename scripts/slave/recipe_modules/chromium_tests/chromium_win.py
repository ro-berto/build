# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import bot_spec


def _chromium_win_spec(**kwargs):
  return bot_spec.BotSpec.create(
      build_gs_bucket='chromium-win-archive', **kwargs)


SPEC = {
    'builders': {
        'WebKit Win10':
            _chromium_win_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'goma_high_parallel',
                    'goma_enable_global_file_stat_cache',
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                bot_type=bot_spec.TESTER,
                tests=[],
                parent_buildername='Win Builder',
                testing={
                    'platform': 'win',
                },
            ),
        'Win Builder':
            _chromium_win_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'goma_high_parallel',
                    'goma_enable_global_file_stat_cache',
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'win',
                },
            ),
        'Win10 Tests x64':
            _chromium_win_spec(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                tests=[],
                parent_buildername='Win x64 Builder',
                testing={
                    'platform': 'win',
                },
            ),
        'Win10 Tests x64 Code Coverage':
            _chromium_win_spec(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['use_clang_coverage'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                tests=[],
                parent_buildername='Win x64 Builder Code Coverage',
                testing={
                    'platform': 'win',
                },
            ),
        'Win7 (32) Tests':
            _chromium_win_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'goma_high_parallel',
                    'goma_enable_global_file_stat_cache',
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='Win Builder',
                testing={
                    'platform': 'win',
                },
            ),
        'Win7 Tests (1)':
            _chromium_win_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'goma_high_parallel',
                    'goma_enable_global_file_stat_cache',
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                bot_type=bot_spec.TESTER,
                tests=[],
                parent_buildername='Win Builder',
                testing={
                    'platform': 'win',
                },
            ),
        'Win x64 Builder':
            _chromium_win_spec(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'win',
                },
            ),
        'Win x64 Builder Code Coverage':
            _chromium_win_spec(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['use_clang_coverage'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'win',
                },
            ),
        'Win 7 Tests x64 (1)':
            _chromium_win_spec(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                tests=[],
                parent_buildername='Win x64 Builder',
                testing={
                    'platform': 'win',
                },
            ),
        'Win x64 Builder (dbg)':
            _chromium_win_spec(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'win',
                },
            ),
        'Win Builder (dbg)':
            _chromium_win_spec(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 32,
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'win',
                },
            ),
        'Win7 Tests (dbg)(1)':
            _chromium_win_spec(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 32,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='Win Builder (dbg)',
                testing={
                    'platform': 'win',
                },
            ),
        'Win10 Tests x64 (dbg)':
            _chromium_win_spec(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='Win x64 Builder (dbg)',
                testing={
                    'platform': 'win',
                },
            ),
    },
}
