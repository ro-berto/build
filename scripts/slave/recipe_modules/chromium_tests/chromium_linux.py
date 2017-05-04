# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-linux-archive',
    # WARNING: src-side runtest.py is only tested with chromium CQ builders.
    # Usage not covered by chromium CQ is not supported and can break
    # without notice.
    'src_side_runtest_py': True,
  },
  'builders': {
    'Linux Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
        'ninja_confirm_noop',
        'chrome_with_codecs',
        'fetch_telemetry_dependencies',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'chromium_swarm_tests',
      ],
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
      'checkout_dir': 'linux',
    },
    'Linux Tests': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'Linux Builder',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'Linux Builder (dbg)(32)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
        'ninja_confirm_noop',
        'fetch_telemetry_dependencies',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'google_apis_unittests',
        'sync_integration_tests',
      ],
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
      'checkout_dir': 'linux',
      # Temporary hack because the binaries are too large to be isolated.
      'GYP_DEFINES': {
        'fastbuild': 2,
      },
    },
    'Linux Tests (dbg)(1)(32)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'Linux Builder (dbg)(32)',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },

    'Linux Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
        'ninja_confirm_noop',
        'fetch_telemetry_dependencies',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
      'checkout_dir': 'linux',
    },
    'Linux Tests (dbg)(1)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'Linux Builder (dbg)',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },

    'Android Arm64 Builder (dbg)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['chrome_with_codecs', 'mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'arm64_builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'Android Builder (dbg)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['chrome_with_codecs', 'mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder',
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
      'checkout_dir': 'android',
    },
    'Android Tests (dbg)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['chrome_with_codecs', 'mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'tester',
      'parent_buildername': 'Android Builder (dbg)',
      'android_config': 'main_builder',
      'root_devices': True,
      'tests': [],
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },

    'Android Builder': {
      'chromium_config': 'android',
      'chromium_apply_config': ['chrome_with_codecs', 'mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder',
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
      'checkout_dir': 'android',
    },

    'Android Tests': {
      'chromium_config': 'android',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'tester',
      'parent_buildername': 'Android Builder',
      'android_config': 'main_builder',
      'root_devices': True,
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },

    'Android Clang Builder (dbg)': {
      'chromium_config': 'android_clang',
      'chromium_apply_config': ['chrome_with_codecs', 'errorprone'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'clang_builder_mb',
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
    },

    'Cast Audio Linux': {
      'chromium_config': 'cast_linux',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'cast_shell',
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Cast Linux': {
      'chromium_config': 'cast_linux',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'cast_shell',
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Cast Android (dbg)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['chrome_with_codecs', 'mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'compile_targets': [
        'cast_shell_apk',
      ],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'cast_builder',
      'testing': {
        'platform': 'linux',
      },
    },
  },
}
