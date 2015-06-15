# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

SPEC = {
  'builders': {
    'Google Chrome ChromeOS': {
      'chromium_config': 'chromium_official',
      'chromium_apply_config': ['chromeos'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'chrome',
        'chrome_sandbox',
        'linux_symbols',
        'symupload'
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Google Chrome Linux': {
      'chromium_config': 'chromium_official',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'testing': {
        'platform': 'linux',
      },
    },
    'Google Chrome Linux x64': {
      'chromium_config': 'chromium_official',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'linux',
      },
    },
    'Google Chrome Mac': {
      'chromium_config': 'chromium_official',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'mac',
      },
    },
    'Google Chrome Win': {
      'chromium_config': 'chromium_official',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'testing': {
        'platform': 'win',
      },
    },
  },
}
