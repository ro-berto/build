# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-mac-archive',
  },
  'builders': {
    'mac-cocoa-rel': {
      'bot_type': 'tester',
      'chromium_apply_config': [
          'mb',
          'ninja_confirm_noop',
      ],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
      },
      'gclient_config': 'chromium',
      'parent_buildername': 'Mac Builder',
      'testing': {
          'platform': 'mac',
      },
    },
    'mac-jumbo-rel': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_apply_config': [
          'mb',
          'ninja_confirm_noop',
      ],
      'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
      },
      'testing': {
          'platform': 'mac',
      },
    },
    'Mac Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
        'ninja_confirm_noop',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'mac',
      },
      'checkout_dir': 'mac',
    },
    'Mac10.13 Tests': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'Mac Builder',
      'testing': {
        'platform': 'mac',
      },
      'swarming_dimensions': {
        'os': 'Mac-10.13',
      },
    },
    'Mac10.10 Tests': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'Mac Builder',
      'testing': {
        'platform': 'mac',
      },
      'swarming_dimensions': {
        'os': 'Mac-10.10',
      },
    },
    'Mac10.11 Tests': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'Mac Builder',
      'testing': {
        'platform': 'mac',
      },
      'swarming_dimensions': {
        'os': 'Mac-10.11',
      },
    },
    'Mac10.12 Tests': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'Mac Builder',
      'testing': {
        'platform': 'mac',
      },
      'swarming_dimensions': {
        'os': 'Mac-10.12',
      },
    },
    'Mac Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
        'ninja_confirm_noop',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'mac',
      },
      'checkout_dir': 'mac',
    },
    'Mac10.13 Tests (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'Mac Builder (dbg)',
      'testing': {
        'platform': 'mac',
      },
      'swarming_dimensions': {
        'os': 'Mac-10.13',
      },
    },
  },
}
