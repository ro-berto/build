# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_spec


def _client_v8_fyi_spec(**kwargs):
  return bot_spec.BotSpec.create(
      build_gs_bucket='chromium-v8', luci_project='v8', **kwargs)


SPEC = {
    'Linux Debug Builder':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            gclient_config='chromium',
            gclient_apply_config=[
                'v8_tot',
                'chromium_lkgr',
                'show_v8_revision',
            ],
            chromium_apply_config=['mb', 'mb_luci_auth'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.BUILDER,
            set_component_rev={
                'name': 'src/v8',
                'rev_str': '%s'
            },
            testing={
                'platform': 'linux',
                'source_side_spec_file': 'chromium.linux.json',
            },
        ),
    'V8 Linux GN':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            gclient_config='chromium',
            gclient_apply_config=[
                'v8_tot',
                'chromium_lkgr',
                'show_v8_revision',
            ],
            chromium_apply_config=['mb', 'mb_luci_auth'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.BUILDER,
            compile_targets=[
                'blink_tests',
                'extensions_browsertests',
                'gin_unittests',
                'pdfium_test',
                'postmortem-metadata',
                'net_unittests',
                'unit_tests',
            ],
            set_component_rev={
                'name': 'src/v8',
                'rev_str': '%s'
            },
            testing={
                'platform': 'linux',
                'source_side_spec_file': 'chromium.linux.json',
            },
        ),
    'V8 Android GN (dbg)':
        _client_v8_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            gclient_config='chromium',
            gclient_apply_config=[
                'android',
                'v8_tot',
                'chromium_lkgr',
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
            },
            android_config='main_builder',
            bot_type=bot_spec.BUILDER,
            compile_targets=[
                'blink_tests',
                'gin_unittests',
                'net_unittests',
            ],
            set_component_rev={
                'name': 'src/v8',
                'rev_str': '%s'
            },
            testing={
                'platform': 'linux',
                'source_side_spec_file': 'chromium.linux.json',
            },
        ),
    'V8 Blink Linux':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            gclient_config='chromium',
            gclient_apply_config=[
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.BUILDER,
            compile_targets=[
                'blink_tests',
            ],
            set_component_rev={
                'name': 'src/v8',
                'rev_str': '%s'
            },
            testing={
                'platform': 'linux',
            },
        ),
    'V8 Blink Linux Debug':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            gclient_config='chromium',
            gclient_apply_config=[
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.BUILDER,
            compile_targets=[
                'blink_tests',
            ],
            set_component_rev={
                'name': 'src/v8',
                'rev_str': '%s'
            },
            testing={
                'platform': 'linux',
            },
        ),
    'V8 Blink Mac':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            gclient_config='chromium',
            gclient_apply_config=[
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.BUILDER,
            compile_targets=[
                'blink_tests',
            ],
            set_component_rev={
                'name': 'src/v8',
                'rev_str': '%s'
            },
            testing={
                'platform': 'mac',
            },
        ),
    'V8 Blink Win':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            gclient_config='chromium',
            gclient_apply_config=[
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            bot_type=bot_spec.BUILDER,
            compile_targets=[
                'blink_tests',
            ],
            set_component_rev={
                'name': 'src/v8',
                'rev_str': '%s'
            },
            testing={
                'platform': 'win',
            },
        ),
    'V8 Blink Linux Future':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            gclient_config='chromium',
            gclient_apply_config=[
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.BUILDER,
            compile_targets=[
                'blink_tests',
            ],
            set_component_rev={
                'name': 'src/v8',
                'rev_str': '%s'
            },
            testing={
                'platform': 'linux',
            },
        ),
    'V8 Blink Linux Layout NG':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            gclient_config='chromium',
            gclient_apply_config=[
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.BUILDER,
            compile_targets=[
                'blink_tests',
            ],
            set_component_rev={
                'name': 'src/v8',
                'rev_str': '%s'
            },
            testing={
                'platform': 'linux',
            },
        ),
    # Bot names should be in sync with chromium.linux's names to retrieve
    # the same test configuration files.
    'Linux Tests (dbg)(1)':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            gclient_config='chromium',
            gclient_apply_config=[
                'v8_tot',
                'chromium_lkgr',
                'show_v8_revision',
            ],
            chromium_apply_config=['mb', 'mb_luci_auth'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.TESTER,
            set_component_rev={
                'name': 'src/v8',
                'rev_str': '%s'
            },
            parent_buildername='Linux Debug Builder',
            testing={
                'platform': 'linux',
                'source_side_spec_file': 'chromium.linux.json',
            },
        ),
    'Linux ASAN Builder':
        _client_v8_fyi_spec(
            chromium_config='chromium_asan',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            gclient_config='chromium',
            gclient_apply_config=[
                'v8_tot',
                'chromium_lkgr',
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.BUILDER,
            compile_targets=[
                'extensions_browsertests',
                'net_unittests',
                'unit_tests',
            ],
            set_component_rev={
                'name': 'src/v8',
                'rev_str': '%s'
            },
            testing={
                'platform': 'linux',
                'source_side_spec_file': 'chromium.memory.json',
            },
        ),
    # GPU bots.
    'Win V8 FYI Release (NVIDIA)':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'v8_tot',
                'chromium_lkgr',
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            bot_type=bot_spec.BUILDER_TESTER,
            compile_targets=[],
            testing={
                'platform': 'win',
            },
            set_component_rev={
                'name': 'src/v8',
                'rev_str': '%s'
            },
            serialize_tests=True,
        ),
    'Mac V8 FYI Release (Intel)':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'v8_tot',
                'chromium_lkgr',
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.BUILDER_TESTER,
            compile_targets=[],
            testing={
                'platform': 'mac',
            },
            set_component_rev={
                'name': 'src/v8',
                'rev_str': '%s'
            },
            serialize_tests=True,
        ),
    'Linux V8 FYI Release (NVIDIA)':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'v8_tot',
                'chromium_lkgr',
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.BUILDER_TESTER,
            compile_targets=[],
            testing={
                'platform': 'linux',
            },
            set_component_rev={
                'name': 'src/v8',
                'rev_str': '%s'
            },
            serialize_tests=True,
        ),
    'Linux V8 FYI Release - pointer compression (NVIDIA)':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'v8_tot',
                'chromium_lkgr',
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.BUILDER_TESTER,
            compile_targets=[],
            testing={
                'platform': 'linux',
            },
            set_component_rev={
                'name': 'src/v8',
                'rev_str': '%s'
            },
            serialize_tests=True,
        ),
    'Android V8 FYI Release (Nexus 5X)':
        _client_v8_fyi_spec(
            chromium_config='android',
            chromium_apply_config=[],
            gclient_config='chromium',
            gclient_apply_config=[
                'android',
                'v8_tot',
                'chromium_lkgr',
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'TARGET_PLATFORM': 'android',
            },
            android_config='arm64_builder_rel_mb',
            bot_type=bot_spec.BUILDER_TESTER,
            compile_targets=[],
            testing={
                'platform': 'linux',
            },
            set_component_rev={
                'name': 'src/v8',
                'rev_str': '%s'
            },
        ),
}
