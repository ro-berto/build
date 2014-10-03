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
      'recipe_config': 'chromium_asan',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {'platform': 'linux'},
      'enable_swarming': True,
      'use_isolate': True,
    },
  },
}

for name in ('Linux ASan LSan Tests (1)',
             'Linux ASan Tests (sandboxed)'):
  SPEC['builders'][name] = {
    'recipe_config': 'chromium_asan',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 64,
    },
    'bot_type': 'tester',
    'test_generators': [
      steps.generate_gtest,
    ],
    'parent_buildername': 'Linux ASan LSan Builder',
    'testing': {'platform': 'linux'},
    'enable_swarming': True,
  }

# LSan is not sandbox-compatible, which is why testers 1-3 have the sandbox
# disabled. This tester runs the same tests again with the sandbox on and LSan
# disabled. This only affects browser tests. See http://crbug.com/336218
SPEC['builders']['Linux ASan Tests (sandboxed)']['chromium_apply_config'] = (
    ['no_lsan'])

for bits, bit_txt in ((32, ''), (64, ' 64')):
  builder_name = 'Mac ASan%s Builder' % bit_txt
  SPEC['builders'][builder_name] = {
    'recipe_config': 'chromium_mac_asan',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': bits,
    },
    'bot_type': 'builder',
    'testing': {'platform': 'mac'},
  }

  for shard in (1, 2, 3):
    name = 'Mac ASan%s Tests (%d)' % (bit_txt, shard)
    SPEC['builders'][name] = {
      'recipe_config': 'chromium_mac_asan',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': bits,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
      ],
      'parent_buildername': builder_name,
      'testing': {'platform': 'mac'},
    }