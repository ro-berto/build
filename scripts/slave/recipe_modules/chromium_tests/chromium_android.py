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
  },
}
