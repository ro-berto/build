# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-win-archive',
  },
  'builders': {
    'Win Builder': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'chromium_builder_tests',
      ],
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
      'use_isolate': True,
    },
    'XP Tests (1)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'parent_buildername': 'Win Builder',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
      'swarming_dimensions': {
        'cpu': 'x86-32',
        'os': 'Windows-5.1',
      },
    },
    'Vista Tests (1)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'parent_buildername': 'Win Builder',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
      'swarming_dimensions': {
        'os': 'Windows-6.0',
      },
    },
    'Win7 Tests (1)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'tests': [
        steps.MiniInstallerTest(),
      ],
      'parent_buildername': 'Win Builder',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'Win x64 Builder': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'all',
      ],
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
      'use_isolate': True,
    },
    'Win 7 Tests x64 (1)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'parent_buildername': 'Win x64 Builder',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },

    'Win x64 Builder (dbg)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'all',
      ],
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
      'use_isolate': True,
    },

    'Win Builder (dbg)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'chromium_builder_tests',
      ],
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
      'use_isolate': True,
    },
    'Win7 Tests (dbg)(1)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'parent_buildername': 'Win Builder (dbg)',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'Win8 Aura': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'disable_runhooks': True,
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'parent_buildername': 'Win Builder (dbg)',
      'testing': {
        'platform': 'win',
      },
      'swarming_dimensions': {
        'os': 'Windows-6.2',
      },
    },
  },
}
