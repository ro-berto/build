# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps


SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-android-archive',
  },
  'builders': {
    'Jelly Bean Tester': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm Builder (dbg)',
      'parent_mastername': 'chromium.android',
      'bot_type': 'tester',
      'android_config': 'main_builder_mb',
      'test_results_config': 'public_server',
      'testing': {
        'platform': 'linux',
      },
    },

    'Lollipop Consumer Tester': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm64 Builder (dbg)',
      'parent_mastername': 'chromium.android',
      'bot_type': 'tester',
      'android_config': 'arm64_builder_mb',
      'test_results_config': 'public_server',
      'testing': {
        'platform': 'linux',
      },
    },

    'Lollipop Low-end Tester': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder_mb',
      'test_results_config': 'public_server',
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

    'NDK Next MIPS Builder': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android', 'ndk_next'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'builder',
      'android_config': 'mipsel_builder_mb',
      'testing': {
        'platform': 'linux',
      },
    },

    'NDK Next x64 Builder': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android', 'ndk_next'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'builder',
      'android_config': 'x64_builder_mb',
      'testing': {
        'platform': 'linux',
      },
    },

    'NDK Next x86 Builder': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android', 'ndk_next'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'builder',
      'android_config': 'x86_builder_mb',
      'testing': {
        'platform': 'linux',
      },
    },
  },
}
