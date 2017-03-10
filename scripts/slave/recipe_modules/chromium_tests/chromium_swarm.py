# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'builders': {
    'Android Swarm': {
      'chromium_config': 'android',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
        'TARGET_ARCH': 'arm',
      },
      'android_config': 'main_builder',
      'testing': {
        'platform': 'linux',
      },
      'bot_type': 'builder_tester',
      'enable_swarming': True,
    },
    'Linux Swarm': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
      },
      'testing': {
        'platform': 'linux',
      },
      'bot_type': 'builder_tester',
      'enable_swarming': True,
    },
    'Mac Swarm': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
      },
      'testing': {
        'platform': 'mac',
      },
      'bot_type': 'builder_tester',
      'enable_swarming': True,
    },
    'Windows Swarm': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
      },
      'testing': {
        'platform': 'win',
      },
      'bot_type': 'builder_tester',
      'enable_swarming': True,
    },
  },
}
