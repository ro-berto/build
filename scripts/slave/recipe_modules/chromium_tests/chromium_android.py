# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-android-archive',
  },
  'builders': {
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
      'bot_type': 'builder_tester',
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
      'bot_type': 'builder_tester',
      'android_config': 'main_builder',
      'root_devices': True,
      'enable_swarming': False,
      'tests': [
        steps.AMPInstrumentationTest(
            test_apk='AndroidWebViewTest',
            apk_under_test='AndroidWebView',
            android_isolate_path=
                'android_webview/android_webview_test_apk.isolate',
            compile_target='android_webview_test_apk',
            device_oem=['Sony'], device_os=['4.4.2'],
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
      ],
      'testing': {
        'platform': 'linux',
      },
    },
  },
}
