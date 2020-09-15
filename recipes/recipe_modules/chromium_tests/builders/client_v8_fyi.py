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
                'chromium_lkgr',
                'show_v8_revision',
            ],
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com/',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'V8 Linux GN':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            gclient_config='chromium',
            gclient_apply_config=[
                'chromium_lkgr',
                'show_v8_revision',
            ],
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com/',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'V8 Android GN (dbg)':
        _client_v8_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com/',
            gclient_config='chromium',
            gclient_apply_config=[
                'android',
                'chromium_lkgr',
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
            },
            android_config='main_builder',
            simulation_platform='linux',
        ),
    'V8 Blink Linux':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com/',
            gclient_config='chromium',
            gclient_apply_config=[
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'V8 Blink Linux Debug':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com/',
            gclient_config='chromium',
            gclient_apply_config=[
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'V8 Blink Mac':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com/',
            gclient_config='chromium',
            gclient_apply_config=[
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='mac',
        ),
    'V8 Blink Win':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com/',
            gclient_config='chromium',
            gclient_apply_config=[
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            simulation_platform='win',
        ),
    'V8 Blink Linux Future':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com/',
            gclient_config='chromium',
            gclient_apply_config=[
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'V8 Blink Linux Layout NG':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com/',
            gclient_config='chromium',
            gclient_apply_config=[
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'Linux ASAN Builder':
        _client_v8_fyi_spec(
            chromium_config='chromium_asan',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com/',
            gclient_config='chromium',
            gclient_apply_config=[
                'chromium_lkgr',
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    # GPU bots.
    'Win V8 FYI Release (NVIDIA)':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            isolate_server='https://isolateserver.appspot.com/',
            gclient_config='chromium',
            gclient_apply_config=[
                'chromium_lkgr',
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Mac V8 FYI Release (Intel)':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            isolate_server='https://isolateserver.appspot.com/',
            gclient_config='chromium',
            gclient_apply_config=[
                'chromium_lkgr',
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='mac',
            serialize_tests=True,
        ),
    'Linux V8 FYI Release (NVIDIA)':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            isolate_server='https://isolateserver.appspot.com/',
            gclient_config='chromium',
            gclient_apply_config=[
                'chromium_lkgr',
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux V8 FYI Release - pointer compression (NVIDIA)':
        _client_v8_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            isolate_server='https://isolateserver.appspot.com/',
            gclient_config='chromium',
            gclient_apply_config=[
                'chromium_lkgr',
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Android V8 FYI Release (Nexus 5X)':
        _client_v8_fyi_spec(
            chromium_config='android',
            chromium_apply_config=[],
            isolate_server='https://isolateserver.appspot.com/',
            gclient_config='chromium',
            gclient_apply_config=[
                'android',
                'chromium_lkgr',
                'show_v8_revision',
            ],
            chromium_config_kwargs={
                'TARGET_PLATFORM': 'android',
            },
            android_config='arm64_builder_rel_mb',
            simulation_platform='linux',
        ),
}
