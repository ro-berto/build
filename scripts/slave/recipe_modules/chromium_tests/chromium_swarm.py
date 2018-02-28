# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'builders': {
    'Android N5 Swarm': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
        'TARGET_ARCH': 'arm',
      },
      'android_config': 'main_builder_mb',
      'testing': {
        'platform': 'linux',
      },
      'bot_type': 'builder_tester',
    },
    'Android N5X Swarm': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android',
        'TARGET_ARCH': 'arm',
      },
      'android_config': 'main_builder_mb',
      'testing': {
        'platform': 'linux',
      },
      'bot_type': 'builder_tester',
    },
    'ChromeOS Swarm': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'chromeos', 'mb', 'ninja_confirm_noop',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_ARCH': 'arm',
        'TARGET_BITS': 64,
        # TODO(bpastene): Change this to kevin when full builds are available.
        'TARGET_CROS_BOARD': 'arm-generic',
        'TARGET_PLATFORM': 'chromeos',
      },
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
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
    },
  },
}
