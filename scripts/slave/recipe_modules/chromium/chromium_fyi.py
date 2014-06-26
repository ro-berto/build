# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-fyi-archive',
  },
  'builders': {
    'Chromium iOS Device': {
      'recipe_config': 'chromium_ios_device',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'ios',
        'TARGET_BITS': 32,
      },
      'gclient_config_kwargs': {
        'GIT_MODE': True,
      },
      'testing': {
        'platform': 'mac',
      }
    },
    'Chromium iOS Simulator (dbg)': {
      'recipe_config': 'chromium_ios_simulator',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'ios',
        'TARGET_BITS': 32,
      },
      'gclient_config_kwargs': {
        'GIT_MODE': True,
      },
      'tests': steps.IOS_TESTS,
      'testing': {
        'platform': 'mac',
      }
    },
    'Chromium iOS Device (ninja)': {
      'recipe_config': 'chromium_ios_ninja',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'ios',
        'TARGET_BITS': 64,
      },
      'gclient_config_kwargs': {
        'GIT_MODE': True,
      },
      'testing': {
        'platform': 'mac',
      }
    },
    'Linux ARM Cross-Compile': {
      # TODO(phajdan.jr): Re-enable goma, http://crbug.com/349236 .
      'recipe_config': 'chromium_no_goma',
      'GYP_DEFINES': {
        'target_arch': 'arm',
        'arm_float_abi': 'hard',
        'test_isolation_mode': 'archive',
      },
      'chromium_config': 'chromium',
      'runhooks_env': {
        'AR': 'arm-linux-gnueabihf-ar',
        'AS': 'arm-linux-gnueabihf-as',
        'CC': 'arm-linux-gnueabihf-gcc',
        'CC_host': 'gcc',
        'CXX': 'arm-linux-gnueabihf-g++',
        'CXX_host': 'g++',
        'RANLIB': 'arm-linux-gnueabihf-ranlib',
      },
      'tests': [
        steps.DynamicGTestTests('Linux ARM Cross-Compile'),
      ],
      'testing': {
        'platform': 'linux',
      },
      'do_not_run_tests': True,
      'use_isolate': True,
    },
    'Linux Trusty': {
      # TODO(phajdan.jr): Re-enable goma, http://crbug.com/349236 .
      'recipe_config': 'chromium_no_goma',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'all',
      ],
      'tests': [
        steps.DynamicGTestTests('Linux Trusty'),
        steps.MojoPythonTests(),
        steps.TelemetryUnitTests(),
        steps.TelemetryPerfUnitTests(),
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux Trusty (32)': {
      # TODO(phajdan.jr): Re-enable goma, http://crbug.com/349236 .
      'recipe_config': 'chromium_no_goma',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'all',
      ],
      'tests': [
        steps.DynamicGTestTests('Linux Trusty (32)'),
        steps.MojoPythonTests(),
        steps.TelemetryUnitTests(),
        steps.TelemetryPerfUnitTests(),
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux Trusty (dbg)': {
      # TODO(phajdan.jr): Re-enable goma, http://crbug.com/349236 .
      'recipe_config': 'chromium_no_goma',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'all',
      ],
      'tests': [
        steps.DynamicGTestTests('Linux Trusty (dbg)'),
        steps.MojoPythonTests(),
        steps.TelemetryUnitTests(),
        steps.TelemetryPerfUnitTests(),
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux Trusty (dbg)(32)': {
      # TODO(phajdan.jr): Re-enable goma, http://crbug.com/349236 .
      'recipe_config': 'chromium_no_goma',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'all',
      ],
      'tests': [
        steps.DynamicGTestTests('Linux Trusty (dbg)(32)'),
        steps.MojoPythonTests(),
        steps.TelemetryUnitTests(),
        steps.TelemetryPerfUnitTests(),
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Linux MSan Builder': {
      'recipe_config': 'chromium_clang',
      'GYP_DEFINES': {
        'msan': 1,
        'use_instrumented_libraries': 1,
        'instrumented_libraries_jobs': 5,
      },
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Linux MSan': {
      'recipe_config': 'chromium_clang',
      'GYP_DEFINES': {
        # Required on testers to pass the right runtime flags.
        # TODO(earthdok): make this part of a chromium_msan recipe config.
        'msan': 1,
      },
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'tests': [
        steps.DynamicGTestTests('Chromium Linux MSan'),
      ],
      'parent_buildername': 'Chromium Linux MSan Builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Linux MSan (browser tests)': {
      'recipe_config': 'chromium_clang',
      'GYP_DEFINES': {
        # Required on testers to pass the right runtime flags.
        # TODO(earthdok): make this part of a chromium_msan recipe config.
        'msan': 1,
      },
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'tests': [
        steps.DynamicGTestTests('Chromium Linux MSan (browser tests)'),
      ],
      'parent_buildername': 'Chromium Linux MSan Builder',
      'testing': {
        'platform': 'linux',
      },
    },
  },
}
