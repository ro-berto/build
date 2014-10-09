# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-fyi-archive',
  },
  'builders': {
    'android_nexus5_oilpan_perf': {
      'disable_tests': True,
      'bot_type': 'tester',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'gclient_config': 'perf',
      'gclient_apply_config': ['android'],
      'parent_buildername': 'android_oilpan_builder',
      'recipe_config': 'perf',
      'android_config': 'perf',
      'testing': {
        'platform': 'linux',
      },
      'tests': [
        steps.AndroidPerfTests('android-nexus5-oilpan', 1),
      ],
    },
    'android_oilpan_builder': {
      'disable_tests': True,
      'recipe_config': 'chromium_oilpan',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_ARCH': 'arm',
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
      'chromium_apply_config': ['chromium_perf', 'android'],
      'gclient_apply_config': ['android', 'perf'],
    },
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
    'Chromium Mac 10.10': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'test_generators': [
        steps.generate_gtest,
      ],
      'tests': [
        steps.NaclIntegrationTest(),
        steps.MojoPythonTests(),
        steps.TelemetryUnitTests(),
        steps.TelemetryPerfUnitTests(),
      ],
      'testing': {
        'platform': 'mac',
      },
    },
    'Linux ARM Cross-Compile': {
      # TODO(phajdan.jr): Re-enable goma, http://crbug.com/349236 .
      'recipe_config': 'chromium_no_goma',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_ARCH': 'arm',
        'TARGET_BITS': 32,
      },
      'GYP_DEFINES': {
        'arm_float_abi': 'hard',
        'test_isolation_mode': 'archive',
      },
      'chromium_config': 'chromium',
      'test_generators': [
        steps.generate_gtest,
      ],
      # TODO(phajdan.jr): Automatically add _run targets when used.
      'compile_targets': [
        'browser_tests_run',
      ],
      'testing': {
        'platform': 'linux',
      },
      'do_not_run_tests': True,
      'use_isolate': True,
    },
    'Linux Trusty': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'all',
      ],
      'test_generators': [
        steps.generate_gtest,
      ],
      'tests': [
        steps.MojoPythonTests(),
        steps.MojoPythonBindingsTests(),
        steps.TelemetryUnitTests(),
        steps.TelemetryPerfUnitTests(),
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux Trusty (32)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'all',
      ],
      'test_generators': [
        steps.generate_gtest,
      ],
      'tests': [
        steps.MojoPythonTests(),
        steps.MojoPythonBindingsTests(),
        steps.TelemetryUnitTests(),
        steps.TelemetryPerfUnitTests(),
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux Trusty (dbg)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'all',
      ],
      'test_generators': [
        steps.generate_gtest,
      ],
      'tests': [
        steps.MojoPythonTests(),
        steps.MojoPythonBindingsTests(),
        steps.TelemetryUnitTests(),
        steps.TelemetryPerfUnitTests(),
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux Trusty (dbg)(32)': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'all',
      ],
      'test_generators': [
        steps.generate_gtest,
      ],
      'tests': [
        steps.MojoPythonTests(),
        steps.MojoPythonBindingsTests(),
        steps.TelemetryUnitTests(),
        steps.TelemetryPerfUnitTests(),
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Print Preview Linux': {
      'recipe_config': 'chromium',
      'GYP_DEFINES': {
        'component': 'shared_library',
      },
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'linux',
        'TARGET_BITS': 64,
      },
      'tests': [
        steps.PrintPreviewTests(),
      ],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
    },
    'Print Preview Mac': {
      'recipe_config': 'chromium',
      'GYP_DEFINES': {
        'component': 'shared_library',
      },
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'mac',
        'TARGET_BITS': 64,
      },
      'tests': [
        steps.PrintPreviewTests(),
      ],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'mac',
      },
    },
    'Print Preview Win': {
      'recipe_config': 'chromium',
      'GYP_DEFINES': {
        'component': 'shared_library',
      },
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'win',
        'TARGET_BITS': 32,
      },
      'tests': [
        steps.PrintPreviewTests(),
      ],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'win',
      },
    },
    'Mac OpenSSL': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'GYP_DEFINES': {
        'use_openssl': '1',
      },
      'test_generators': [
        steps.generate_gtest,
      ],
      'testing': {
        'platform': 'mac',
      },
    },
    'Site Isolation Linux': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'content_unittests',
        'content_browsertests',
      ],
      'test_generators': [
        steps.generate_gtest,
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Site Isolation Win': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'win',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'content_unittests',
        'content_browsertests',
        'crash_service',
      ],
      'test_generators': [
        steps.generate_gtest,
      ],
      'testing': {
        'platform': 'win',
      },
    },
    'Chromium Linux ChromeOS MSan Builder': {
      'recipe_config': 'chromium_msan',
      'chromium_apply_config': ['instrumented_libraries'],
      'GYP_DEFINES': {
        'msan_track_origins': 0,
        'chromeos': 1
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
    'Linux ChromeOS MSan Tests': {
      'recipe_config': 'chromium_msan',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
      ],
      'parent_buildername': 'Chromium Linux ChromeOS MSan Builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux ChromeOS MSan Browser (1)': {
      'recipe_config': 'chromium_msan',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
      ],
      'parent_buildername': 'Chromium Linux ChromeOS MSan Builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux ChromeOS MSan Browser (2)': {
      'recipe_config': 'chromium_msan',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
      ],
      'parent_buildername': 'Chromium Linux ChromeOS MSan Builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux ChromeOS MSan Browser (3)': {
      'recipe_config': 'chromium_msan',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
      ],
      'parent_buildername': 'Chromium Linux ChromeOS MSan Builder',
      'testing': {
        'platform': 'linux',
      },
    },
  },
}
