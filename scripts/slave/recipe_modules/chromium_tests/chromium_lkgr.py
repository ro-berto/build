# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import bot_spec

RESULTS_URL = 'https://chromeperf.appspot.com'

SPEC = {
    'builders': {
        'Win ASan Release':
            bot_spec.BotSpec.create(
                chromium_config='chromium_win_clang_asan',
                chromium_apply_config=['mb', 'clobber'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                disable_tests=True,
                cf_archive_build=True,
                cf_gs_bucket='chromium-browser-asan',
                cf_gs_acl='public-read',
                cf_archive_name='asan',
                compile_targets=['chromium_builder_asan'],
                testing={'platform': 'win'},
            ),
        'Win ASan Release Media':
            bot_spec.BotSpec.create(
                chromium_config='chromium_win_clang_asan',
                chromium_apply_config=[
                    'mb',
                    'clobber',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                bot_type=bot_spec.BUILDER,
                disable_tests=True,
                cf_archive_build=True,
                cf_gs_bucket='chrome-test-builds/media',
                cf_gs_acl='public-read',
                cf_archive_name='asan',
                compile_targets=['chromium_builder_asan'],
                testing={'platform': 'win'},
            ),
        'Mac ASAN Release':
            bot_spec.BotSpec.create(
                chromium_config='chromium_asan',
                chromium_apply_config=['mb', 'clobber'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                disable_tests=True,
                cf_archive_build=True,
                cf_gs_bucket='chromium-browser-asan',
                cf_gs_acl='public-read',
                cf_archive_name='asan',
                compile_targets=['chromium_builder_asan'],
                testing={'platform': 'mac'},
            ),
        'Mac ASAN Release Media':
            bot_spec.BotSpec.create(
                chromium_config='chromium_asan',
                chromium_apply_config=[
                    'mb',
                    'clobber',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                disable_tests=True,
                cf_archive_build=True,
                cf_gs_bucket='chrome-test-builds/media',
                cf_gs_acl='public-read',
                cf_archive_name='asan',
                compile_targets=['chromium_builder_asan'],
                testing={'platform': 'mac'},
            ),
        'Mac ASAN Debug':
            bot_spec.BotSpec.create(
                chromium_config='chromium_asan',
                chromium_apply_config=['mb', 'clobber'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                disable_tests=True,
                cf_archive_build=True,
                cf_gs_bucket='chromium-browser-asan',
                cf_gs_acl='public-read',
                cf_archive_name='asan',
                compile_targets=['chromium_builder_asan'],
                testing={'platform': 'mac'},
            ),
        'ASAN Release':
            bot_spec.BotSpec.create(
                chromium_config='chromium_asan',
                chromium_apply_config=['mb', 'clobber'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                cf_archive_build=True,
                cf_gs_bucket='chromium-browser-asan',
                cf_gs_acl='public-read',
                cf_archive_name='asan',
                testing={'platform': 'linux'},
            ),
        'ASAN Release Media':
            bot_spec.BotSpec.create(
                chromium_config='chromium_asan',
                chromium_apply_config=['mb', 'clobber'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                disable_tests=True,
                cf_archive_build=True,
                cf_gs_bucket='chrome-test-builds/media',
                cf_gs_acl='public-read',
                cf_archive_name='asan',
                compile_targets=['chromium_builder_asan'],
                testing={'platform': 'linux'},
            ),
        'ASAN Debug':
            bot_spec.BotSpec.create(
                chromium_config='chromium_asan',
                chromium_apply_config=['mb', 'clobber'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                disable_tests=True,
                cf_archive_build=True,
                cf_gs_bucket='chromium-browser-asan',
                cf_gs_acl='public-read',
                cf_archive_name='asan',
                compile_targets=['chromium_builder_asan'],
                testing={'platform': 'linux'},
            ),
        'ChromiumOS ASAN Release':
            bot_spec.BotSpec.create(
                chromium_config='chromium_asan',
                chromium_apply_config=['mb', 'clobber'],
                gclient_config='chromium',
                gclient_apply_config=['chromeos'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                disable_tests=True,
                cf_archive_build=True,
                cf_gs_bucket='chromium-browser-asan',
                cf_gs_acl='public-read',
                cf_archive_name='asan',
                cf_archive_subdir_suffix='chromeos',
                compile_targets=['chromium_builder_asan'],
                testing={'platform': 'linux'},
            ),
        # The build process is described at
        # https://sites.google.com/a/chromium.org/dev/developers/testing/addresssanitizer#TOC-Building-with-v8_target_arch-arm
        'ASan Debug (32-bit x86 with V8-ARM)':
            bot_spec.BotSpec.create(
                chromium_config='chromium_asan',
                chromium_apply_config=['mb', 'clobber'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 32,
                },
                bot_type=bot_spec.BUILDER,
                disable_tests=True,
                cf_archive_build=True,
                cf_gs_bucket='chromium-browser-asan',
                cf_gs_acl='public-read',
                cf_archive_name='asan-v8-arm',
                cf_archive_subdir_suffix='v8-arm',
                compile_targets=['chromium_builder_asan'],
                testing={'platform': 'linux'},
            ),
        'ASan Release (32-bit x86 with V8-ARM)':
            bot_spec.BotSpec.create(
                chromium_config='chromium_asan',
                chromium_apply_config=['mb', 'clobber'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                bot_type=bot_spec.BUILDER,
                disable_tests=True,
                cf_archive_build=True,
                cf_gs_bucket='chromium-browser-asan',
                cf_gs_acl='public-read',
                cf_archive_name='asan-v8-arm',
                cf_archive_subdir_suffix='v8-arm',
                compile_targets=['chromium_builder_asan'],
                testing={'platform': 'linux'},
            ),
        'ASan Release Media (32-bit x86 with V8-ARM)':
            bot_spec.BotSpec.create(
                chromium_config='chromium_asan',
                chromium_apply_config=['mb', 'clobber'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                bot_type=bot_spec.BUILDER,
                disable_tests=True,
                cf_archive_build=True,
                cf_gs_bucket='chrome-test-builds/media',
                cf_gs_acl='public-read',
                cf_archive_name='asan-v8-arm',
                cf_archive_subdir_suffix='v8-arm',
                compile_targets=['chromium_builder_asan'],
                testing={'platform': 'linux'},
            ),
        # The build process for TSan is described at
        # http://dev.chromium.org/developers/testing/threadsanitizer-tsan-v2
        'TSAN Release':
            bot_spec.BotSpec.create(
                chromium_config='chromium_clang',
                chromium_apply_config=['mb', 'tsan2', 'clobber'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                disable_tests=True,
                cf_archive_build=True,
                cf_gs_bucket='chromium-browser-tsan',
                cf_gs_acl='public-read',
                cf_archive_name='tsan',
                compile_targets=['chromium_builder_asan'],
                testing={'platform': 'linux'},
            ),
        'TSAN Debug':
            bot_spec.BotSpec.create(
                chromium_config='chromium_clang',
                chromium_apply_config=['mb', 'tsan2', 'clobber'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                disable_tests=True,
                cf_archive_build=True,
                cf_gs_bucket='chromium-browser-tsan',
                cf_gs_acl='public-read',
                cf_archive_name='tsan',
                compile_targets=['chromium_builder_asan'],
                testing={'platform': 'linux'},
            ),
        # The build process for MSan is described at
        # http://dev.chromium.org/developers/testing/memorysanitizer
        'MSAN Release (no origins)':
            bot_spec.BotSpec.create(
                chromium_config='chromium_clang',
                chromium_apply_config=['mb', 'msan', 'clobber'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                disable_tests=True,
                cf_archive_build=True,
                cf_gs_bucket='chromium-browser-msan',
                cf_gs_acl='public-read',
                cf_archive_name='msan-no-origins',
                compile_targets=['chromium_builder_asan'],
                testing={'platform': 'linux'},
            ),
        'MSAN Release (chained origins)':
            bot_spec.BotSpec.create(
                chromium_config='chromium_clang',
                chromium_apply_config=['mb', 'msan', 'clobber'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                disable_tests=True,
                cf_archive_build=True,
                cf_gs_bucket='chromium-browser-msan',
                cf_gs_acl='public-read',
                cf_archive_name='msan-chained-origins',
                compile_targets=['chromium_builder_asan'],
                testing={'platform': 'linux'},
            ),
        'UBSan Release':
            bot_spec.BotSpec.create(
                chromium_config='chromium_linux_ubsan',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                disable_tests=True,
                cf_archive_build=True,
                cf_gs_bucket='chromium-browser-ubsan',
                cf_gs_acl='public-read',
                cf_archive_name='ubsan',
                compile_targets=['chromium_builder_asan'],
                testing={'platform': 'linux'},
            ),
        # The build process for UBSan vptr is described at
        # http://dev.chromium.org/developers/testing/undefinedbehaviorsanitizer
        'UBSan vptr Release':
            bot_spec.BotSpec.create(
                chromium_config='chromium_linux_ubsan_vptr',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                disable_tests=True,
                cf_archive_build=True,
                cf_gs_bucket='chromium-browser-ubsan',
                cf_gs_acl='public-read',
                cf_archive_name='ubsan-vptr',
                cf_archive_subdir_suffix='vptr',
                compile_targets=['chromium_builder_asan'],
                testing={'platform': 'linux'},
            ),
    },
}
