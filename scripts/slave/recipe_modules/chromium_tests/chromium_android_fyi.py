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


    # These don't actually run on the master. They're here to configure
    # stand-alone trybots on tryserver.chromium.android.
    'Unswarmed N5 Tests Dummy Builder': {
      'chromium_config': 'android',
      'chromium_apply_config': ['chrome_with_codecs'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder_mb',
      'android_apply_config': ['use_devil_provision'],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
    },
    'Unswarmed N5X Tests Dummy Builder': {
      'chromium_config': 'android',
      'chromium_apply_config': ['chrome_with_codecs'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'arm64_builder_mb',
      'android_apply_config': ['use_devil_provision'],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
    },

    'Nougat Phone Tester': {
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
      'android_apply_config': ['use_devil_provision'],
      'testing': {
        'platform': 'linux',
      },
    },

    'x64 Device Tester': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'builder_tester',
      'android_config': 'x64_builder_mb',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
      'compile_targets': [
        'all',
      ],
    },

    'x86 Cloud Tester': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'builder_tester',
      'android_config': 'x86_builder_mb',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
    },
  },
}
