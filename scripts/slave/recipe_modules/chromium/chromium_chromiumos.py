# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-chromiumos-archive',
  },
  'builders': {
    'Linux ChromiumOS Full': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['chromeos'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'app_list_unittests',
        'aura_builder',
        'base_unittests',
        'browser_tests',
        'cacheinvalidation_unittests',
        'chromeos_unittests',
        'components_unittests',
        'compositor_unittests',
        'content_browsertests',
        'content_unittests',
        'crypto_unittests',
        'dbus_unittests',
        'device_unittests',
        'gcm_unit_tests',
        'google_apis_unittests',
        'gpu_unittests',
        'interactive_ui_tests',
        'ipc_tests',
        'jingle_unittests',
        'media_unittests',
        'message_center_unittests',
        'nacl_loader_unittests',
        'net_unittests',
        'ppapi_unittests',
        'printing_unittests',
        'remoting_unittests',
        'sandbox_linux_unittests',
        'sql_unittests',
        'sync_unit_tests',
        'ui_base_unittests',
        'unit_tests',
        'url_unittests',
        'views_unittests',
      ],
      'tests': [
        steps.ArchiveBuildStep(
            'chromium-browser-snapshots',
            gs_acl='public-read',
        ),
      ],
      'testing': {
        'platform': 'linux',
      },
    },

    'Linux ChromiumOS Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['chromeos'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'aura_builder',
      ],
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
      'use_isolate': True,
    },
    'Linux ChromiumOS Tests (1)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['chromeos'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'parent_buildername': 'Linux ChromiumOS Builder',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },

    'Linux ChromiumOS (Clang dbg)': {
      'chromium_config': 'chromium_clang',
      'chromium_apply_config': ['chromeos'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'app_list_unittests',
        'aura_builder',
        'base_unittests',
        'browser_tests',
        'cacheinvalidation_unittests',
        'chromeos_unittests',
        'components_unittests',
        'compositor_unittests',
        'content_browsertests',
        'content_unittests',
        'crypto_unittests',
        'dbus_unittests',
        'device_unittests',
        'gcm_unit_tests',
        'google_apis_unittests',
        'gpu_unittests',
        'interactive_ui_tests',
        'ipc_tests',
        'jingle_unittests',
        'media_unittests',
        'message_center_unittests',
        'nacl_loader_unittests',
        'net_unittests',
        'ppapi_unittests',
        'printing_unittests',
        'remoting_unittests',
        'sandbox_linux_unittests',
        'sql_unittests',
        'sync_unit_tests',
        'ui_base_unittests',
        'unit_tests',
        'url_unittests',
        'views_unittests',
      ],
      'testing': {
        'platform': 'linux',
      },
    },

    'Linux ChromiumOS Ozone Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['chromeos', 'ozone'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'aura_builder',
      ],
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
      'use_isolate': True,
    },
    'Linux ChromiumOS Ozone Tests (1)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['chromeos', 'ozone'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'parent_buildername': 'Linux ChromiumOS Ozone Builder',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
      'use_isolate': True,
    },
    'Linux ChromiumOS Ozone Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['chromeos', 'ozone'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'aura_builder',
      ],
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
      'use_isolate': True,
    },
    'Linux ChromiumOS Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['chromeos'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'aura_builder',
      ],
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
      'use_isolate': True,
    },
    'Linux ChromiumOS Tests (dbg)(1)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['chromeos'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'parent_buildername': 'Linux ChromiumOS Builder (dbg)',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },

    # Simple Chrome test builder for coverage
    'Coverage ChromiumOS Simple Chrome x86-generic': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['chromeos'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'chromeos',
        'TARGET_CROS_BOARD': 'x86-generic',
      },
      'bot_type': 'builder',
      'disable_tests': True,
      'compile_targets': [
        'chrome',
      ],
      'archive_key': 'commit_position',
      'testing': {
        'platform': 'linux',
      },
    },
  },
}
