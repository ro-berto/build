# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-android-archive',
  },
  'builders': {
    'Android arm Builder (dbg)': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder',
      'compile_targets': [
        'android_builder_tests'
      ],
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },

    'Android arm64 Builder (dbg)': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder',
      'compile_targets': [
        'android_builder_tests'
      ],
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },

    'Android Remoting Tests': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'compile_targets': [
        'remoting_apk',
      ],
      'parent_buildername': 'Android arm Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder',
      'root_devices': True,
      'tests': [
        steps.GTestTest('remoting_unittests'),
        steps.AndroidInstrumentationTest(
            'ChromotingTest', 'remoting_test_apk',
            adb_install_apk='Chromoting.apk'),
      ],
      'testing': {
        'platform': 'linux',
      },
    },

    'Android WebView (amp)': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder',
      'enable_swarming': False,
      'tests': [
        steps.AMPInstrumentationTest(
            test_apk='AndroidWebViewTest',
            apk_under_test='AndroidWebView',
            android_isolate_path=
                'android_webview/android_webview_test_apk.isolate',
            compile_target='android_webview_test_apk',
            device_name=['Nexus 7'], device_os=['4.4.2'],
            fallback_to_local=False),
        steps.AMPInstrumentationTest(
            test_apk='AndroidWebViewTest',
            apk_under_test='AndroidWebView',
            android_isolate_path=
                'android_webview/android_webview_test_apk.isolate',
            compile_target='android_webview_test_apk',
            device_oem=['Motorola', 'motorola'], device_os=['4.4.2'],
            fallback_to_local=False),
        steps.AMPInstrumentationTest(
            test_apk='AndroidWebViewTest',
            apk_under_test='AndroidWebView',
            android_isolate_path=
                'android_webview/android_webview_test_apk.isolate',
            compile_target='android_webview_test_apk',
            device_oem=['Samsung', 'samsung'], device_os=['4.4.2'],
            fallback_to_local=False),
      ],
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'testing': {
        'platform': 'linux',
      },
    },
  },
}
