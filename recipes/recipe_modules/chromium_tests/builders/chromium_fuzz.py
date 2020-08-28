# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_spec

RESULTS_URL = 'https://chromeperf.appspot.com'

SPEC = {
    'Win ASan Release':
        bot_spec.BotSpec.create(
            chromium_config='chromium_win_clang_asan',
            chromium_apply_config=['mb', 'clobber'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            cf_archive_build=True,
            cf_gs_bucket='chromium-browser-asan',
            cf_gs_acl='public-read',
            cf_archive_name='asan',
            simulation_platform='win',
        ),
    'Win ASan Release Media':
        bot_spec.BotSpec.create(
            chromium_config='chromium_win_clang_asan',
            chromium_apply_config=[
                'mb',
                'clobber',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            cf_archive_build=True,
            cf_gs_bucket='chrome-test-builds/media',
            cf_gs_acl='public-read',
            cf_archive_name='asan',
            simulation_platform='win',
        ),
    'Mac ASAN Release':
        bot_spec.BotSpec.create(
            chromium_config='chromium_asan',
            chromium_apply_config=['mb', 'clobber'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            cf_archive_build=True,
            cf_gs_bucket='chromium-browser-asan',
            cf_gs_acl='public-read',
            cf_archive_name='asan',
            simulation_platform='mac',
        ),
    'Mac ASAN Release Media':
        bot_spec.BotSpec.create(
            chromium_config='chromium_asan',
            chromium_apply_config=[
                'mb',
                'clobber',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            cf_archive_build=True,
            cf_gs_bucket='chrome-test-builds/media',
            cf_gs_acl='public-read',
            cf_archive_name='asan',
            simulation_platform='mac',
        ),
    'ASAN Release':
        bot_spec.BotSpec.create(
            chromium_config='chromium_asan',
            chromium_apply_config=['mb', 'clobber'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            cf_archive_build=True,
            cf_gs_bucket='chromium-browser-asan',
            cf_gs_acl='public-read',
            cf_archive_name='asan',
            simulation_platform='linux',
        ),
    'ASAN Release Media':
        bot_spec.BotSpec.create(
            chromium_config='chromium_asan',
            chromium_apply_config=['mb', 'clobber'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            cf_archive_build=True,
            cf_gs_bucket='chrome-test-builds/media',
            cf_gs_acl='public-read',
            cf_archive_name='asan',
            simulation_platform='linux',
        ),
    'ASAN Debug':
        bot_spec.BotSpec.create(
            # Maybe remove the 'chromium_asan' config if this builder is
            # removed.
            chromium_config='chromium_asan',
            chromium_apply_config=['mb', 'clobber'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            cf_archive_build=True,
            cf_gs_bucket='chromium-browser-asan',
            cf_gs_acl='public-read',
            cf_archive_name='asan',
            simulation_platform='linux',
        ),
    'ChromiumOS ASAN Release':
        bot_spec.BotSpec.create(
            # Maybe remove the 'chromium_asan' config if this builder is
            # removed.
            chromium_config='chromium_asan',
            chromium_apply_config=['mb', 'clobber'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['chromeos'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            cf_archive_build=True,
            cf_gs_bucket='chromium-browser-asan',
            cf_gs_acl='public-read',
            cf_archive_name='asan',
            cf_archive_subdir_suffix='chromeos',
            simulation_platform='linux',
        ),
    # The build process is described at
    # https://sites.google.com/a/chromium.org/dev/developers/testing/addresssanitizer#TOC-Building-with-v8_target_arch-arm
    'ASan Debug (32-bit x86 with V8-ARM)':
        bot_spec.BotSpec.create(
            # Maybe remove the 'chromium_asan' config if this builder is
            # removed.
            chromium_config='chromium_asan',
            chromium_apply_config=['mb', 'clobber'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
            },
            cf_archive_build=True,
            cf_gs_bucket='chromium-browser-asan',
            cf_gs_acl='public-read',
            cf_archive_name='asan-v8-arm',
            cf_archive_subdir_suffix='v8-arm',
            simulation_platform='linux',
        ),
    'ASan Release (32-bit x86 with V8-ARM)':
        bot_spec.BotSpec.create(
            chromium_config='chromium_asan',
            chromium_apply_config=['mb', 'clobber'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            cf_archive_build=True,
            cf_gs_bucket='chromium-browser-asan',
            cf_gs_acl='public-read',
            cf_archive_name='asan-v8-arm',
            cf_archive_subdir_suffix='v8-arm',
            simulation_platform='linux',
        ),
    'ASan Release Media (32-bit x86 with V8-ARM)':
        bot_spec.BotSpec.create(
            chromium_config='chromium_asan',
            chromium_apply_config=['mb', 'clobber'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            cf_archive_build=True,
            cf_gs_bucket='chrome-test-builds/media',
            cf_gs_acl='public-read',
            cf_archive_name='asan-v8-arm',
            cf_archive_subdir_suffix='v8-arm',
            simulation_platform='linux',
        ),
    # The build process for TSan is described at
    # http://dev.chromium.org/developers/testing/threadsanitizer-tsan-v2
    'TSAN Release':
        bot_spec.BotSpec.create(
            chromium_config='chromium_clang',
            chromium_apply_config=['mb', 'tsan2', 'clobber'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            cf_archive_build=True,
            cf_gs_bucket='chromium-browser-tsan',
            cf_gs_acl='public-read',
            cf_archive_name='tsan',
            simulation_platform='linux',
        ),
    'TSAN Debug':
        bot_spec.BotSpec.create(
            chromium_config='chromium_clang',
            chromium_apply_config=['mb', 'tsan2', 'clobber'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            cf_archive_build=True,
            cf_gs_bucket='chromium-browser-tsan',
            cf_gs_acl='public-read',
            cf_archive_name='tsan',
            simulation_platform='linux',
        ),
    # The build process for MSan is described at
    # http://dev.chromium.org/developers/testing/memorysanitizer
    'MSAN Release (no origins)':
        bot_spec.BotSpec.create(
            chromium_config='chromium_clang',
            chromium_apply_config=['mb', 'msan', 'clobber'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            cf_archive_build=True,
            cf_gs_bucket='chromium-browser-msan',
            cf_gs_acl='public-read',
            cf_archive_name='msan-no-origins',
            simulation_platform='linux',
        ),
    'MSAN Release (chained origins)':
        bot_spec.BotSpec.create(
            chromium_config='chromium_clang',
            chromium_apply_config=['mb', 'msan', 'clobber'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            cf_archive_build=True,
            cf_gs_bucket='chromium-browser-msan',
            cf_gs_acl='public-read',
            cf_archive_name='msan-chained-origins',
            simulation_platform='linux',
        ),
    'UBSan Release':
        bot_spec.BotSpec.create(
            chromium_config='chromium_linux_ubsan',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            cf_archive_build=True,
            cf_gs_bucket='chromium-browser-ubsan',
            cf_gs_acl='public-read',
            cf_archive_name='ubsan',
            simulation_platform='linux',
        ),
    # The build process for UBSan vptr is described at
    # http://dev.chromium.org/developers/testing/undefinedbehaviorsanitizer
    'UBSan vptr Release':
        bot_spec.BotSpec.create(
            chromium_config='chromium_linux_ubsan_vptr',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            cf_archive_build=True,
            cf_gs_bucket='chromium-browser-ubsan',
            cf_gs_acl='public-read',
            cf_archive_name='ubsan-vptr',
            cf_archive_subdir_suffix='vptr',
            simulation_platform='linux',
        ),
}
