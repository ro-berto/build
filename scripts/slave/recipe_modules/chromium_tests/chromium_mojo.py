# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'builders': {
    'Chromium Mojo Android': {
      'chromium_config': 'android',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'android_config': 'main_builder',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'android',
        'TARGET_ARCH': 'arm',
        'TARGET_BITS': 32,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_instrumentation_test,
        steps.generate_isolated_script,
        steps.generate_script,
      ],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Mojo Linux': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'linux',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Mojo Windows': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'win',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder_tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'testing': {
        'platform': 'win',
      },
    },
  },
}
