# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-linux-archive',
  },
  'builders': {
    'Linux Builder': {
      'recipe_config': 'chromium',
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
      'use_isolate': True,
      'enable_swarming': True,
    },
    'Linux Tests': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'parent_buildername': 'Linux Builder',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'Linux Builder (dbg)(32)': {
      'recipe_config': 'chromium',
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
      'use_isolate': True,
      'enable_swarming': True,
      # Temporary hack because the binaries are too large to be isolated.
      'GYP_DEFINES': {
        'fastbuild': 2,
      },
    },
    'Linux Tests (dbg)(1)(32)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'parent_buildername': 'Linux Builder (dbg)(32)',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },

    'Linux Builder (dbg)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
      'use_isolate': True,
    },
    'Linux Tests (dbg)(1)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'parent_buildername': 'Linux Builder (dbg)',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },

    'Android Arm64 Builder (dbg)': {
      'recipe_config': 'chromium_android',
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
      'recipe_config': 'chromium_android',
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
    },
    'Android Tests (dbg)': {
      'recipe_config': 'chromium_android',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'tester',
      'parent_buildername': 'Android Builder (dbg)',
      'android_config': 'main_builder',
      'root_devices': True,
      'tests': [
        steps.AndroidInstrumentationTest(
            'AndroidWebViewTest', 'android_webview_test_apk',
            isolate_file_path='android_webview/android_webview_test_apk.isolate',
            adb_install_apk=(
                'AndroidWebView.apk', 'org.chromium.android_webview.shell')),
        steps.AndroidInstrumentationTest(
            'ChromeShellTest', 'chrome_shell_test_apk',
            isolate_file_path='chrome/chrome_shell_test_apk.isolate',
            adb_install_apk=(
                'ChromeShell.apk', 'org.chromium.chrome.shell')),
        steps.AndroidInstrumentationTest(
            'ContentShellTest', 'content_shell_test_apk',
            isolate_file_path='content/content_shell_test_apk.isolate',
            adb_install_apk=(
                'ContentShell.apk', 'org.chromium.content_shell_apk')),
        steps.AndroidInstrumentationTest(
            'ChromeSyncShellTest', 'chrome_sync_shell_test_apk',
            adb_install_apk=(
                'ChromeSyncShell.apk', 'org.chromium.chrome.browser.sync')),
        steps.GTestTest('android_webview_unittests'),
        steps.GTestTest('base_unittests'),
        steps.GTestTest(
            'breakpad_unittests',
            override_compile_targets=['breakpad_unittests_deps'],
            android_isolate_path='breakpad/breakpad_unittests.isolate'),
        steps.GTestTest('cc_unittests'),
        steps.GTestTest('components_unittests'),
        steps.GTestTest('content_browsertests'),
        steps.GTestTest('content_unittests'),
        steps.GTestTest('device_unittests'),
        steps.GTestTest('events_unittests'),
        steps.GTestTest('gl_tests'),
        steps.GTestTest('gpu_unittests'),
        steps.GTestTest('ipc_tests'),
        steps.GTestTest('media_unittests'),
        steps.GTestTest('net_unittests'),
        steps.GTestTest(
            'sandbox_linux_unittests',
            override_compile_targets=['sandbox_linux_unittests_deps']),
        steps.GTestTest('sql_unittests'),
        steps.GTestTest('sync_unit_tests'),
        steps.GTestTest('ui_android_unittests'),
        steps.GTestTest('ui_base_unittests'),
        steps.GTestTest('ui_touch_selection_unittests'),
        steps.GTestTest('unit_tests'),
        steps.AndroidJunitTest('junit_unit_tests'),
        steps.AndroidJunitTest('chrome_junit_tests'),
        steps.AndroidJunitTest('content_junit_tests'),
      ],
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'testing': {
        'platform': 'linux',
      },
    },

    'Android Builder': {
      'recipe_config': 'chromium_android',
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
    },
    'Android Tests': {
      'recipe_config': 'chromium_android',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'tester',
      'parent_buildername': 'Android Builder',
      'android_config': 'main_builder',
      'root_devices': True,
      'tests': [
        steps.AndroidInstrumentationTest(
            'AndroidWebViewTest', 'android_webview_test_apk',
            isolate_file_path='android_webview/android_webview_test_apk.isolate',
            adb_install_apk=(
                'AndroidWebView.apk', 'org.chromium.android_webview.shell')),
        steps.AndroidInstrumentationTest(
            'ChromeShellTest', 'chrome_shell_test_apk',
            isolate_file_path='chrome/chrome_shell_test_apk.isolate',
            adb_install_apk=(
                'ChromeShell.apk', 'org.chromium.chrome.shell')),
        steps.AndroidInstrumentationTest(
            'ContentShellTest', 'content_shell_test_apk',
            isolate_file_path='content/content_shell_test_apk.isolate',
            adb_install_apk=(
                'ContentShell.apk', 'org.chromium.content_shell_apk')),
        steps.AndroidInstrumentationTest(
            'ChromeSyncShellTest', 'chrome_sync_shell_test_apk',
            adb_install_apk=(
                'ChromeSyncShell.apk', 'org.chromium.chrome.browser.sync')),
        steps.GTestTest('android_webview_unittests'),
        steps.GTestTest('base_unittests'),
        steps.GTestTest(
            'breakpad_unittests',
            override_compile_targets=['breakpad_unittests_deps'],
            android_isolate_path='breakpad/breakpad_unittests.isolate'),
        steps.GTestTest('cc_unittests'),
        steps.GTestTest('components_unittests'),
        steps.GTestTest('content_browsertests'),
        steps.GTestTest('content_unittests'),
        steps.GTestTest('events_unittests'),
        steps.GTestTest('gl_tests'),
        steps.GTestTest('gpu_unittests'),
        steps.GTestTest('ipc_tests'),
        steps.GTestTest('media_unittests'),
        steps.GTestTest('net_unittests'),
        steps.GTestTest(
            'sandbox_linux_unittests',
            override_compile_targets=['sandbox_linux_unittests_deps']),
        steps.GTestTest('sql_unittests'),
        steps.GTestTest('sync_unit_tests'),
        steps.GTestTest('ui_android_unittests'),
        steps.GTestTest('ui_base_unittests'),
        steps.GTestTest('ui_touch_selection_unittests'),
        steps.GTestTest('unit_tests'),
        steps.AndroidJunitTest('junit_unit_tests'),
        steps.AndroidJunitTest('chrome_junit_tests'),
        steps.AndroidJunitTest('content_junit_tests'),
      ],
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'testing': {
        'platform': 'linux',
      },
    },

    'Android Clang Builder (dbg)': {
      'recipe_config': 'chromium_android_clang',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'clang_builder',
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
    },

    'Android x86 Builder (dbg)': {
      'recipe_config': 'chromium_android',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'x86_builder',
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },
  },
}
