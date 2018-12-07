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
    # TODO(jbudorick): Move the three cronet bots over to chromium.android.
    'Android Cronet ARMv6 Builder': {
      'android_config': 'main_builder_mb',
      'bot_type': 'builder_tester',
      'chromium_config': 'main_builder_mb',
      'chromium_apply_config': [
        'cronet_builder',
        'cronet_official',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'testing': {
        'platform': 'linux',
      }
    },
    'Android Cronet Builder (dbg)': {
      'android_config': 'main_builder_mb',
      'bot_type': 'builder_tester',
      'chromium_config': 'main_builder_mb',
      'chromium_apply_config': [
        'cronet_builder',
        'cronet_official',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'testing': {
        'platform': 'linux',
      },
    },
    'Android Cronet KitKat Builder': {
      'android_config': 'main_builder_mb',
      'bot_type': 'builder_tester',
      'chromium_config': 'main_builder_mb',
      'chromium_apply_config': [
        'cronet_builder',
        'cronet_official',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'testing': {
        'platform': 'linux',
      }
    },
    'Android WebView O NetworkService (dbg)': {
      'chromium_config': 'android',
      'chromium_apply_config': [
        'download_vr_test_apks',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm64 Builder (dbg)',
      'parent_mastername': 'chromium.android',
      'bot_type': 'tester',
      'android_config': 'main_builder_mb',
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

    'NDK Next arm Builder': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android', 'ndk_next'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'builder',
      'android_config': 'main_builder_mb',
      'testing': {
        'platform': 'linux',
      },
    },

    'NDK Next arm64 Builder': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android', 'ndk_next'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'builder',
      'android_config': 'arm64_builder_mb',
      'testing': {
        'platform': 'linux',
      },
    },

    'Nougat Phone Tester': {
      'chromium_config': 'android',
      'chromium_apply_config': [
        'download_vr_test_apks',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm64 Builder (dbg)',
      'parent_mastername': 'chromium.android',
      'bot_type': 'tester',
      'android_config': 'main_builder_mb',
      'android_apply_config': ['use_devil_provision'],
      'testing': {
        'platform': 'linux',
      },
    },

  },
}
