# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

RESULTS_URL = 'https://chromeperf.appspot.com'

SPEC = {
    'settings': {
        'build_gs_bucket': 'chromium-android-archive',
    },
    'builders': {
        'Android WebView P FYI (rel)': {
            'chromium_config': 'android',
            'chromium_apply_config': ['mb'],
            'gclient_config': 'chromium',
            'gclient_apply_config': ['android'],
            'chromium_config_kwargs': {
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            'android_config': 'main_builder',
            'bot_type': 'builder_tester',
            'testing': {
                'platform': 'linux',
            },
        },
        'Memory Infra Tester': {
            'chromium_config': 'android',
            'gclient_config': 'chromium',
            'gclient_apply_config': ['android'],
            'chromium_config_kwargs': {
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            'bot_type': 'builder_tester',
            'android_config': 'main_builder_mb',
            'testing': {
                'platform': 'linux',
            },
        },
        'android-marshmallow-x86-fyi-rel': {
            'chromium_config': 'android',
            'chromium_apply_config': ['mb'],
            'gclient_config': 'chromium',
            'gclient_apply_config': ['android'],
            'chromium_config_kwargs': {
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            'android_config': 'x86_builder',
            'bot_type': 'builder_tester',
            'testing': {
                'platform': 'linux',
            },
        },
        'android-pie-x86-fyi-rel': {
            'chromium_config': 'android',
            'chromium_apply_config': ['mb'],
            'gclient_config': 'chromium',
            'gclient_apply_config': ['android'],
            'chromium_config_kwargs': {
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            'android_config': 'x86_builder',
            'bot_type': 'builder_tester',
            'testing': {
                'platform': 'linux',
            },
        },
        'android-bfcache-debug': {
            'chromium_config': 'android',
            'gclient_config': 'chromium',
            'gclient_apply_config': ['android'],
            'chromium_config_kwargs': {
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            'android_config': 'main_builder_mb',
            'bot_type': 'builder_tester',
            'testing': {
                'platform': 'linux',
            },
        },
    },
}
