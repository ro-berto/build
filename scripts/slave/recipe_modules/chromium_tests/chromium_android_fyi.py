# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps


SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-android-archive',
  },
  'builders': {
    'Android Tests (trial)(dbg)': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'tester',
      'parent_mastername': 'chromium.android',
      'parent_buildername': 'Android arm Builder (dbg)',
      'android_config': 'non_device_wipe_provisioning',
      'remove_system_webview': True,
      'root_devices': True,
      'tests': [
        steps.GTestTest('gfx_unittests'),
      ],
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
    },

    'Test Run with Tracing': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'tester',
      'parent_mastername': 'chromium.android',
      'parent_buildername': 'Android arm Builder (dbg)',
      'android_config': 'non_device_wipe_provisioning',
      'root_devices': True,
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
    },

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
      'android_apply_config': ['use_devil_provision'],
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
      'android_apply_config': ['use_devil_provision'],
      'test_results_config': 'public_server',
      'test_results_config': 'public_server',
      'testing': {
        'platform': 'linux',
      },
    },

    'Lollipop Low-end Tester': {
      'enable_swarming': True,
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
      'android_apply_config': ['use_devil_provision'],
      'test_results_config': 'public_server',
      'test_results_config': 'public_server',
      'testing': {
        'platform': 'linux',
      },
    },

    'Memory Infra Tester': {
      'enable_swarming': True,
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
      'test_results_config': 'public_server',
      'test_results_config': 'public_server',
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
      'test_results_config': 'public_server',
      'test_results_config': 'public_server',
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
    },

    'Nougat Phone Tester': {
      'enable_swarming': True,
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
      'test_results_config': 'public_server',
      'test_results_config': 'public_server',
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
      'enable_swarming': True,
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
      'enable_swarming': True,
    },
  },
}
