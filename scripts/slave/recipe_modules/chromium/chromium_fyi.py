# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-fyi-archive',
  },
  'builders': {
     'Linux ChromiumOS Athena Builder': {
       'recipe_config': 'chromium_chromeos_athena',
       'chromium_config_kwargs': {
         'BUILD_CONFIG': 'Release',
         'TARGET_BITS': 64,
       },
       'bot_type': 'builder',
       'compile_targets': [
         'athena_unittests',
         'browser_tests',
         'chrome',
       ],
       'testing': {
         'platform': 'linux',
       },
     },
     'Linux ChromiumOS Athena Tests (1)': {
       'recipe_config': 'chromium_chromeos_athena',
       'chromium_config_kwargs': {
         'BUILD_CONFIG': 'Release',
         'TARGET_BITS': 64,
       },
       'bot_type': 'tester',
       'test_generators': [
         steps.generate_gtest,
         steps.generate_script,
       ],
       'parent_buildername': 'Linux ChromiumOS Athena Builder',
       'testing': {
         'platform': 'linux',
       },
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
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
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
        steps.generate_script,
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
        steps.generate_script,
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
        steps.generate_script,
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
        steps.generate_script,
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
        steps.generate_script,
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
        steps.generate_script,
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
        steps.generate_script,
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
        steps.generate_script,
      ],
      'testing': {
        'platform': 'win',
      },
    },
    'Browser Side Navigation Linux': {
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
        steps.generate_script,
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Win PGO Builder': {
      'recipe_config': 'chromium',
      'chromium_config_instrument': 'chromium_pgo_instrument',
      'chromium_config_optimize': 'chromium_pgo_optimize',
      'gclient_config': 'chromium_lkgr',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'testing': {
        'platform': 'win',
      },
    },
    'ChromiumPractice': {
      'recipe_config': 'chromium_blink_merged',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'ChromiumPracticeTester': {
      'recipe_config': 'chromium_blink_merged',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'tests': [
        steps.BlinkTest(),
      ],
      'bot_type': 'tester',
      'parent_buildername': 'ChromiumPractice',
      'testing': {
        'platform': 'linux',
      },
    },
    'ChromiumPracticeFullTester': {
      'recipe_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'blink_tests',
        'chromium_swarm_tests',
      ],
      'tests': [
        steps.BlinkTest(),
      ],
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'CrWinClang': {
      'recipe_config': 'chromium_win_clang',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'win',
      },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'disable_tests': True
    },
    'CrWinClang tester': {
      'recipe_config': 'chromium_no_goma',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'test_generators': [
        steps.generate_gtest,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'CrWinClang',
      'testing': {
        'platform': 'win',
      },
    },
  },
}
