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
      'ninja_confirm_noop',
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
    'checkout_dir': 'win',
  },
  'WebKit Win10': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['mb'],
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
    'checkout_dir': 'win',
  },
  'WebKit Mac Builder': {
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
  'WebKit Mac10.13 (retina)': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['mb'],
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
    'checkout_dir': 'mac',
  },
  'WebKit Linux Trusty ASAN': {
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
    'checkout_dir': 'linux_layout',
  },
  'WebKit Linux Trusty MSAN': {
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
    'checkout_dir': 'linux_layout',
  },
  'Android Builder': {
    'chromium_config': 'android',
    'chromium_apply_config': ['mb'],
    'gclient_config': 'chromium',
    'gclient_apply_config': ['android'],
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 32,
      'TARGET_PLATFORM': 'android',
    },
    'android_config': 'main_builder',
    'bot_type': 'builder',
    'testing': {
      'platform': 'linux',
    },
  },
  'WebKit Android (Nexus4)': {
    'chromium_config': 'android',
    'chromium_apply_config': ['mb'],
    'gclient_config': 'chromium',
    'gclient_apply_config': ['android'],
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 32,
      'TARGET_PLATFORM': 'android',
    },
    'bot_type': 'tester',
    'parent_buildername': 'Android Builder',
    'android_config': 'main_builder',
    'root_devices': True,
    'tests': [
      steps.LocalGTestTest('blink_heap_unittests'),
      steps.LocalGTestTest('webkit_unit_tests'),
      # TODO(crbug.com/875172): this bot can't yet run SwiftShader, so
      # attempt to run layout tests on top of the real GPU instead.
      steps.BlinkTest(extra_args=[
        '--additional-driver-flag=--use-gpu-in-tests']),
    ],
    'testing': {
      'platform': 'linux',
    },
  },
  'WebKit Linux Trusty Leak': {
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
