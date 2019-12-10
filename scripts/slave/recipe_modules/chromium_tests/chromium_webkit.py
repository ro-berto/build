# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-webkit-archive',
  },
}

SPEC['builders'] = {
  'WebKit Win Builder': {
    'chromium_config': 'chromium',
    'chromium_apply_config': [
      'goma_high_parallel',
      'goma_enable_global_file_stat_cache',
      'mb',
    ],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 32,
    },
    'bot_type': 'builder',
    'testing': {
      'platform': 'win',
    },
  },
  'WebKit Win10': {
    'chromium_config': 'chromium',
    'chromium_apply_config': [
      'goma_high_parallel',
      'goma_enable_global_file_stat_cache',
      'mb',
    ],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 32,
    },
    'bot_type': 'tester',
    'parent_buildername': 'WebKit Win Builder',
    'tests': [],
    'testing': {
      'platform': 'win',
    },
  },
  'WebKit Mac Builder': {
    'chromium_config': 'chromium',
    'chromium_apply_config': [
      'mb',
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
  },
  'WebKit Mac10.13 (retina)': {
    'chromium_config': 'chromium',
    'chromium_apply_config': [
      'mb',
    ],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 64,
    },
    'bot_type': 'tester',
    'parent_buildername': 'WebKit Mac Builder',
    'testing': {
      'platform': 'mac',
    },
  },
  'WebKit Linux ASAN': {
    'chromium_config': 'chromium_clang',
    'chromium_apply_config': ['asan', 'mb'],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 64,
    },
    'tests': [],
    'testing': {
      'platform': 'linux',
    },
  },
  'WebKit Linux MSAN': {
    'chromium_config': 'chromium_clang',
    'gclient_config': 'chromium',
    'chromium_apply_config': [
      'mb',
      'msan',
    ],
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 64,
    },
    'tests': [],
    'testing': {
      'platform': 'linux',
    },
  },
  'WebKit Linux Leak': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['mb'],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 64,
    },
    'compile_targets': [
      'blink_tests',
    ],
    'tests': [],
    'testing': {
      'platform': 'linux',
    },
  },
}
