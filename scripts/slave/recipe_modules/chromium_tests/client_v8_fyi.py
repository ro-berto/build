# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-v8',
    'luci_project': 'v8',
  },
  'builders': {
    'Linux Debug Builder': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'gclient_apply_config': [
        'v8_tot',
        'chromium_lkgr',
        'show_v8_revision',
      ],
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      'testing': {
        'platform': 'linux',
        'test_spec_file': 'chromium.linux.json',
      },
    },
    'V8 Linux GN': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'gclient_apply_config': [
        'v8_tot',
        'chromium_lkgr',
        'show_v8_revision',
      ],
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'blink_tests',
        'extensions_browsertests',
        'gin_unittests',
        'pdfium_test',
        'postmortem-metadata',
        'net_unittests',
        'unit_tests',
      ],
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      'testing': {
        'platform': 'linux',
        'test_spec_file': 'chromium.linux.json',
      },
    },
    'Android Builder': {
      'chromium_config': 'main_builder_rel_mb',
      'chromium_apply_config': ['android'],
      'gclient_config': 'chromium',
      'gclient_apply_config': [
        'android',
        'chromium_lkgr',
        'perf',
        'show_v8_revision',
        'v8_tot',
      ],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'android',
        'TARGET_ARCH': 'arm',
      },
      'android_config': 'main_builder_rel_mb',
      'android_apply_config': ['use_devil_adb'],
      'bot_type': 'builder',
      'compile_targets': [
        'android_tools',
        'cc_perftests',
        'chrome_public_apk',
        'gpu_perftests',
        'push_apps_to_background_apk',
        'system_webview_apk',
        'system_webview_shell_apk',
      ],
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      'testing': {
        'platform': 'linux',
        'test_spec_file': 'chromium.linux.json',
      },
    },
    'V8 Android GN (dbg)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': [
        'android',
        'v8_tot',
        'chromium_lkgr',
        'show_v8_revision',
      ],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
        'TARGET_ARCH': 'arm',
      },
      'android_config': 'main_builder',
      'bot_type': 'builder',
      'compile_targets': [
        'blink_tests',
        'gin_unittests',
        'net_unittests',
      ],
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      'testing': {
        'platform': 'linux',
        'test_spec_file': 'chromium.linux.json',
      },
    },
    # Bot names should be in sync with chromium.linux's names to retrieve the
    # same test configuration files.
    'Linux Tests (dbg)(1)': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'gclient_apply_config': [
        'v8_tot',
        'chromium_lkgr',
        'show_v8_revision',
      ],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      'parent_buildername': 'Linux Debug Builder',
      'testing': {
        'platform': 'linux',
        'test_spec_file': 'chromium.linux.json',
      },
    },
    'Linux ASAN Builder': {
      'chromium_config': 'chromium_asan',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': [
        'v8_tot',
        'chromium_lkgr',
        'show_v8_revision',
      ],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'extensions_browsertests',
        'net_unittests',
        'unit_tests',
      ],
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      'testing': {
        'platform': 'linux',
        'test_spec_file': 'chromium.memory.json',
      },
    },
    'Linux Snapshot Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': [
        'v8_tot',
        'chromium_lkgr',
        'show_v8_revision',
      ],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      'archive_build': True,
      'gs_bucket': 'chromium-v8-snapshots',
      'gs_acl': 'public-read',
      'testing': {
        'platform': 'linux',
        'test_spec_file': 'chromium.linux.json',
      },
    },
    # GPU bots.
    'Win V8 FYI Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
        'ninja_confirm_noop',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': [
        'v8_tot',
        'chromium_lkgr',
        'show_v8_revision',
      ],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'win',
      },
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      'serialize_tests': True,
    },
    'Mac V8 FYI Release (Intel)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
        'ninja_confirm_noop',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': [
        'v8_tot',
        'chromium_lkgr',
        'show_v8_revision',
      ],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'mac',
      },
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      'serialize_tests': True,
    },
    'Linux V8 FYI Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
        'ninja_confirm_noop',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': [
        'v8_tot',
        'chromium_lkgr',
        'show_v8_revision',
      ],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'linux',
      },
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      'serialize_tests': True,
    },
    'Linux V8 FYI Release - concurrent marking (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
        'ninja_confirm_noop',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': [
        'v8_tot',
        'chromium_lkgr',
        'show_v8_revision',
      ],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'linux',
      },
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      'serialize_tests': True,
    },
    'Android V8 FYI Release (Nexus 5X)': {
      'chromium_config': 'android',
      'chromium_apply_config': [
        'ninja_confirm_noop',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': [
        'android',
        'v8_tot',
        'chromium_lkgr',
        'show_v8_revision',
      ],
      'chromium_config_kwargs': {
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'arm64_builder_rel_mb',
      'bot_type': 'builder_tester',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'linux',
      },
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      'checkout_dir': 'android',
    },
  },
}
