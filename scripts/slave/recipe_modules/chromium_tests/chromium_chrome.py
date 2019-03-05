# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

RESULTS_URL = 'https://chromeperf.appspot.com'

SPEC = {
  'builders': {
    'chromeos-amd64-generic-google-rel': {
      'chromium_config': 'chromium_official',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': [
          'chrome_internal', 'chromeos_amd64_generic'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_ARCH': 'intel',
        'TARGET_BITS': 64,
        'TARGET_CROS_BOARD': 'amd64-generic',
        'TARGET_PLATFORM': 'chromeos',
      },
      'testing': {
        'platform': 'linux',
      },
    },
    'Google Chrome ChromeOS': {
      # TODO(mmoss): These should all use 'chromium_official_internal', once
      # that's fixed to set the correct mb_config.pyl path.
      'chromium_config': 'chromium_official',
      'chromium_apply_config': [
          'mb',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal', 'chromeos'],
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
    'Google Chrome Linux x64': {
      'chromium_config': 'chromium_official',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'chrome/installer/linux'
      ],
      'testing': {
        'platform': 'linux',
      },
      'tests': {
        steps.SizesStep(RESULTS_URL, 'Google Chrome Linux x64')
      },
    },
    'Google Chrome Mac': {
      'chromium_config': 'chromium_official',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'chrome',
      ],
      'testing': {
        'platform': 'mac',
      },
      'tests': {
        steps.SizesStep(RESULTS_URL, 'Google Chrome Mac')
      },
    },
    'Google Chrome Win': {
      'chromium_config': 'chromium_official',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'compile_targets': [
        'chrome_official_builder',
      ],
      'checkout_dir': 'win_chrome',
      'testing': {
        'platform': 'win',
      },
      'tests': {
        steps.SizesStep(RESULTS_URL, 'Google Chrome Win')
      },
    },
  },
}
