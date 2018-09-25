# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-win-archive',
  },
  'builders': {
    'win-jumbo-rel': {
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
          'platform': 'win',
      },
    },
    'Win Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'goma_high_parallel',
        'goma_enable_global_file_stat_cache',
        'mb',
        'ninja_confirm_noop',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder',
      'checkout_dir': 'win',
      'testing': {
        'platform': 'win',
      },
    },
    'Win10 Tests x64': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'tests': [
        steps.MiniInstallerTest(),
      ],
      'parent_buildername': 'Win x64 Builder',
      'checkout_dir': 'win',
      'testing': {
        'platform': 'win',
      },
      'swarming_dimensions': {
        'cpu': 'x86-64',
        'os': 'Windows-10-15063',
      },
    },
    'Win7 (32) Tests': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'goma_high_parallel',
        'goma_enable_global_file_stat_cache',
        'mb',
        'ninja_confirm_noop',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'Win Builder',
      'checkout_dir': 'win',
      'testing': {
        'platform': 'win',
      },
      'swarming_dimensions': {
        'cpu': 'x86-32',
        'os': 'Windows-7-SP1',
      },
    },
    'Win7 Tests (1)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'goma_high_parallel',
        'goma_enable_global_file_stat_cache',
        'mb',
        'ninja_confirm_noop',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'tests': [
        steps.MiniInstallerTest(),
      ],
      'parent_buildername': 'Win Builder',
      'checkout_dir': 'win',
      'testing': {
        'platform': 'win',
      },
    },
    'Win x64 Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'checkout_dir': 'win',
      'testing': {
        'platform': 'win',
      },
    },
    'Win 7 Tests x64 (1)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'tests': [
        steps.MiniInstallerTest(),
      ],
      'parent_buildername': 'Win x64 Builder',
      'checkout_dir': 'win',
      'testing': {
        'platform': 'win',
      },
    },
    'Win x64 Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'checkout_dir': 'win',
      'testing': {
        'platform': 'win',
      },
    },

    'Win Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder',
      'checkout_dir': 'win',
      'testing': {
        'platform': 'win',
      },
    },
    'Win7 Tests (dbg)(1)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'Win Builder (dbg)',
      'checkout_dir': 'win',
      'testing': {
        'platform': 'win',
      },
    },
    'Win10 Tests x64 (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'Win x64 Builder (dbg)',
      'checkout_dir': 'win',
      'testing': {
        'platform': 'win',
      },
      'swarming_dimensions': {
        'cpu': 'x86-64',
        'os': 'Windows-10-15063',
      },
    },
  },
}
