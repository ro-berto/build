# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-memory-archive',
  },
  'builders': {
    'Linux ASan LSan Builder': {
      'recipe_config': 'chromium_linux_asan',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {'platform': 'linux'},
      'enable_swarming': True,
      'use_isolate': True,
    },
    'Linux ASan LSan Tests (1)': {
      'recipe_config': 'chromium_linux_asan',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'parent_buildername': 'Linux ASan LSan Builder',
      'testing': {'platform': 'linux'},
      'enable_swarming': True,
    },
    'Linux ASan Tests (sandboxed)': {
      'recipe_config': 'chromium_linux_asan',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      # LSan is not sandbox-compatible, which is why testers 1-3 have the
      # sandbox disabled. This tester runs the same tests again with the sandbox
      # on and LSan disabled. This only affects browser tests. See
      # http://crbug.com/336218
      'chromium_apply_config': ['no_lsan'],
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'parent_buildername': 'Linux ASan LSan Builder',
      'testing': {'platform': 'linux'},
      'enable_swarming': True,
    },
    'Mac ASan Builder': {
      'recipe_config': 'chromium_mac_asan',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder',
      'testing': {'platform': 'mac'},
      'enable_swarming': True,
      'use_isolate': True,
    },
    'Mac ASan Tests (1)': {
      'recipe_config': 'chromium_mac_asan',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'parent_buildername': 'Mac ASan Builder',
      'testing': {'platform': 'mac'},
      'enable_swarming': True,
    },
    'Mac ASan 64 Builder': {
      'recipe_config': 'chromium_mac_asan',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {'platform': 'mac'},
      'enable_swarming': True,
      'use_isolate': True,
    },
    'Mac ASan 64 Tests (1)': {
      'recipe_config': 'chromium_mac_asan',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'parent_buildername': 'Mac ASan 64 Builder',
      'testing': {'platform': 'mac'},
      'enable_swarming': True,
    },
    'Linux Chromium OS ASan LSan Builder': {
      'recipe_config': 'chromium_chromiumos_asan',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {'platform': 'linux'},
      'enable_swarming': True,
      'use_isolate': True,
    },
    'Linux Chromium OS ASan LSan Tests (1)': {
      'recipe_config': 'chromium_chromiumos_asan',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'parent_buildername': 'Linux Chromium OS ASan LSan Builder',
      'bot_type': 'tester',
      'testing': {'platform': 'linux'},
      'enable_swarming': True,
    },
  },
}
