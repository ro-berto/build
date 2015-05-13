# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

RESULTS_URL = 'https://chromeperf.appspot.com'

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-fyi-archive',
  },
  'builders': {
     'Chromium iOS Device': {
      'chromium_config': 'chromium_ios_device',
      'gclient_config': 'ios',
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
      'chromium_config': 'chromium_ios_simulator',
      'gclient_config': 'ios',
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
      'chromium_config': 'chromium_ios_ninja',
      'gclient_config': 'ios',
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
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
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
      'chromium_config': 'chromium_no_goma',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_ARCH': 'arm',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder',
      'GYP_DEFINES': {
        'arm_float_abi': 'hard',
        'test_isolation_mode': 'archive',
      },
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
      'use_isolate': True,
    },
    'Linux ARM': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_ARCH': 'arm',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder',
      'GYP_DEFINES': {
        'arm_float_abi': 'hard',
      },
      'use_isolate': True,
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux Trusty': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
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
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
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
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
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
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
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
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
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
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
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
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
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
    'CFI Linux': {
      'chromium_config': 'chromium_cfi',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
    },
    'Mac OpenSSL': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
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
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'GYP_DEFINES': {
        'dcheck_always_on': '1',
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
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'win',
        'TARGET_BITS': 64,
      },
      'GYP_DEFINES': {
        'dcheck_always_on': '1',
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
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
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
    'ChromiumPractice': {
      'chromium_config': 'chromium',
      'gclient_config': 'blink_merged',
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
      'chromium_config': 'chromium',
      'gclient_config': 'blink_merged',
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
      'chromium_config': 'chromium',
      'gclient_config': 'blink_merged',
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
      'chromium_config': 'chromium_win_clang_official',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'win',
      },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'CrWinClang tester': {
      'chromium_config': 'chromium_no_goma',
      'gclient_config': 'chromium',
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
      'enable_swarming': True,
    },
    'CrWinClang(dbg)': {
      'chromium_config': 'chromium_win_clang',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      # Recipes builds Debug builds with component=shared_library by default.
      'bot_type': 'builder',
      'testing': {
        'platform': 'win',
      },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'CrWinClang(dbg) tester': {
      'chromium_config': 'chromium_no_goma',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'test_generators': [
        steps.generate_gtest,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'CrWinClang(dbg)',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'CrWinClang(shared)': {
      'chromium_config': 'chromium_win_clang',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'GYP_DEFINES': { 'component': 'shared_library' },
      'bot_type': 'builder',
      'testing': {
        'platform': 'win',
      },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'CrWinClang(shared) tester': {
      'chromium_config': 'chromium_no_goma',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'test_generators': [
        steps.generate_gtest,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'CrWinClang(shared)',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'CrWinClang64': {
      'chromium_config': 'chromium_win_clang_official',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'win',
      },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'CrWinClang64 tester': {
      'chromium_config': 'chromium_no_goma',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'CrWinClang64',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'CrWinClang64(dbg)': {
      'chromium_config': 'chromium_win_clang',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      # Recipes builds Debug builds with component=shared_library by default.
      'bot_type': 'builder',
      'testing': {
        'platform': 'win',
      },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'CrWinClang64(dbg) tester': {
      'chromium_config': 'chromium_no_goma',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'CrWinClang64(dbg)',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'CrWinClang64(dll)': {
      'chromium_config': 'chromium_win_clang',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'GYP_DEFINES': { 'component': 'shared_library' },
      'bot_type': 'builder',
      'testing': {
        'platform': 'win',
      },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'CrWinClang64(dll) tester': {
      'chromium_config': 'chromium_no_goma',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'CrWinClang64(dll)',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'CrWinClangLLD': {
      'chromium_config': 'chromium_win_clang',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'GYP_DEFINES': { 'component': 'shared_library', 'use_lld': 1 },
      'bot_type': 'builder',
      'testing': {
        'platform': 'win',
      },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'CrWinClangLLD tester': {
      'chromium_config': 'chromium_no_goma',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'test_generators': [
        steps.generate_gtest,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'CrWinClangLLD',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'CrWinAsan': {
      'chromium_config': 'chromium_win_clang_asan',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'win',
      },
      'use_isolate': True,
      'enable_swarming': True,
      # TODO(thakis): Consider using chromium_builder_asan instead?
      'compile_targets': [ 'chromium_builder_tests' ],
      # add_tests_as_compile_targets not needed for the asan bot, it doesn't
      # build everything.
    },
    'CrWinAsan tester': {
      'chromium_config': 'chromium_win_asan',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'test_generators': [
        steps.generate_gtest,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'CrWinAsan',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'CrWinAsan(dll)': {
      'chromium_config': 'chromium_win_clang_asan',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'GYP_DEFINES': { 'component': 'shared_library' },
      'bot_type': 'builder',
      'testing': {
        'platform': 'win',
      },
      'use_isolate': True,
      'enable_swarming': True,
      # TODO(thakis): Consider using chromium_builder_asan instead?
      'compile_targets': [ 'chromium_builder_tests' ],
      # add_tests_as_compile_targets not needed for the asan bot, it doesn't
      # build everything.
    },
    'CrWinAsan(dll) tester': {
      'chromium_config': 'chromium_win_asan',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'test_generators': [
        steps.generate_gtest,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'CrWinAsan(dll)',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'CrWinGoma': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'compile_targets': [ 'chromium_builder_tests' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'testing': {
        'platform': 'win'
      }
    },
    'CrWinGoma(dll)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary', 'shared_library'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'compile_targets': [ 'chromium_builder_tests' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'testing': {
        'platform': 'win'
      }
    },
    'CrWin7Goma': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'compile_targets': [ 'chromium_builder_tests' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'testing': {
        'platform': 'win'
      }
    },
    'CrWin7Goma(dll)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary', 'shared_library'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'compile_targets': [ 'chromium_builder_tests' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'testing': {
        'platform': 'win'
      }
    },
    'CrWin7Goma(dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary'],
      'gclient_config': 'chromium',
      'GYP_DEFINES': {
        'win_z7': '1'
      },
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'compile_targets': [ 'chromium_builder_tests' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'testing': {
        'platform': 'win'
      }
    },
    'CrWin7Goma(clbr)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary', 'clobber', 'shared_library'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'compile_targets': [ 'chromium_builder_tests' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'testing': {
        'platform': 'win'
      }
    },
    'CrWinClangGoma': {
      'chromium_config': 'chromium_win_clang_goma',
      'chromium_apply_config': ['goma_canary', 'clobber'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'compile_targets': [ 'chromium_builder_tests' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'testing': {
        'platform': 'win'
      }
    },
    'Chromium Linux Goma Canary': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [ 'chromium_builder_tests' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'testing': {
        'platform': 'linux'
      }
    },
    'Chromium Linux Goma Canary (clobber)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary', 'clobber'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [ 'chromium_builder_tests' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'testing': {
        'platform': 'linux'
      }
    },
    'Chromium Linux32 Goma Canary (clobber)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary', 'clobber'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'compile_targets': [ 'chromium_builder_tests' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'testing': {
        'platform': 'linux'
      }
    },
    'Chromium Linux Precise Goma LinkTest': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary', 'goma_linktest'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [ 'chromium_builder_tests' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'testing': {
        'platform': 'linux'
      }
    },
    'Chromium Mac 10.6 Goma Canary': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [ 'chromium_builder_tests' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'testing': {
        'platform': 'mac'
      }
    },
    'Chromium Mac 10.7 Goma Canary': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [ 'chromium_builder_tests' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'testing': {
        'platform': 'mac'
      }
    },
    'Chromium Mac 10.6 Goma Canary (clobber)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary', 'clobber'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [ 'chromium_builder_tests' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'testing': {
        'platform': 'mac'
      }
    },
    'Chromium Mac 10.7 Goma Canary (clobber)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary', 'clobber'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [ 'chromium_builder_tests' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'testing': {
        'platform': 'mac'
      }
    },
    'ClangToTLinux': {
      'chromium_config': 'clang_tot_linux',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'GYP_DEFINES': {
        'component': 'shared_library',
        'werror': '',

        # Enable debug info, as on official builders, to catch issues with
        # optimized debug info.
        'linux_dump_symbols': '1',

        # Plugin flags often need to be changed when using a plugin newer than
        # the latest Clang package, so disable plugins.
        'clang_use_chrome_plugins': '0',
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
      'tests': {
        steps.SizesStep(RESULTS_URL, 'ClangToTLinux')
      },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ClangToTLinux tester': {
      'chromium_config': 'chromium_no_goma',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'ClangToTLinux',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'ClangToTLinux (dbg)': {
      'chromium_config': 'clang_tot_linux',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'GYP_DEFINES': {
        'werror': '',

        # Plugin flags often need to be changed when using a plugin newer than
        # the latest Clang package, so disable plugins.
        'clang_use_chrome_plugins': '0',
      },
      'bot_type': 'builder',
      'testing': { 'platform': 'linux', },
      'tests': {
        steps.SizesStep(RESULTS_URL, 'ClangToTLinux (dbg)')
      },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ClangToTLinuxASan': {
      'chromium_config': 'clang_tot_linux_asan',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'chromium_apply_config': ['lsan'],
      'GYP_DEFINES': {
        'werror': '',
        # Plugin flags often need to be changed when using a plugin newer than
        # the latest Clang package, so disable plugins.
        'clang_use_chrome_plugins': '0',
      },
      'bot_type': 'builder',
      'testing': { 'platform': 'linux', },
      'tests': {
        steps.SizesStep(RESULTS_URL, 'ClangToTLinuxASan')
      },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ClangToTLinuxASan tester': {
      'chromium_config': 'chromium_linux_asan',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'chromium_apply_config': ['lsan'],
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'ClangToTLinuxASan',
      'testing': { 'platform': 'linux', },
      'enable_swarming': True,
    },
    'ClangToTAndroidASan': {
      'chromium_config': 'clang_tot_android_asan',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
        'TARGET_ARCH': 'arm',
        'TARGET_BITS': 32,
      },
      'GYP_DEFINES': {
        'component': 'shared_library',
        'werror': '',
        # Plugin flags often need to be changed when using a plugin newer than
        # the latest Clang package, so disable plugins.
        'clang_use_chrome_plugins': '0',
      },
      'bot_type': 'builder',
      'android_config': 'clang_asan_tot_release_builder',
      'testing': { 'platform': 'linux', },
      'tests': {
        steps.SizesStep(RESULTS_URL, 'ClangToTAndroidASan')
      },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ClangToTMac': {
      'chromium_config': 'clang_tot_mac',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'GYP_DEFINES': {
        'component': 'shared_library',
        'werror': '',
        # Plugin flags often need to be changed when using a plugin newer than
        # the latest Clang package, so disable plugins.
        'clang_use_chrome_plugins': '0',
      },
      'bot_type': 'builder',
      'testing': { 'platform': 'mac', },
      'tests': {
        steps.SizesStep(RESULTS_URL, 'ClangToTMac')
      },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ClangToTMac tester': {
      'chromium_config': 'chromium_no_goma',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'ClangToTMac',
      'testing': {
        'platform': 'mac',
      },
      'enable_swarming': True,
    },
    'ClangToTMac (dbg)': {
      'chromium_config': 'clang_tot_mac',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'GYP_DEFINES': {
        'werror': '',
        # Plugin flags often need to be changed when using a plugin newer than
        # the latest Clang package, so disable plugins.
        'clang_use_chrome_plugins': '0',
      },
      'bot_type': 'builder',
      'testing': { 'platform': 'mac', },
      'tests': {
        steps.SizesStep(RESULTS_URL, 'ClangToTMac (dbg)')
      },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ClangToTMacASan': {
      'chromium_config': 'clang_tot_mac_asan',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'GYP_DEFINES': {
        'werror': '',
        # Plugin flags often need to be changed when using a plugin newer than
        # the latest Clang package, so disable plugins.
        'clang_use_chrome_plugins': '0',
      },
      'bot_type': 'builder',
      'testing': { 'platform': 'mac', },
      'tests': {
        steps.SizesStep(RESULTS_URL, 'ClangToTMacASan')
      },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ClangToTMacASan tester': {
      'chromium_config': 'chromium_mac_asan',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'ClangToTMacASan',
      'testing': { 'platform': 'mac', },
      'enable_swarming': True,
    },
    'Linux Builder (clobber)': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['clobber'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        # chromium_tests.analyze treats "all" compile target in a special way;
        # Make sure to trigger it to make sure we respect compile targets
        # returned by gyp analyzer.
        'all',
      ],
      'testing': {
        'platform': 'linux',
      },
    },

    'Android Tests (trial)(dbg)': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'tester',
      'parent_buildername': 'Android Builder (dbg)',
      'android_config': 'main_builder',
      'root_devices': True,
      'tests': [
        steps.AndroidJunitTest('base_junit_tests'),
        steps.GTestTest('components_browsertests'),
        steps.GTestTest('gfx_unittests'),
        steps.GTestTest('gl_unittests'),
      ],
      'testing': {
        'platform': 'linux',
      },
    },

    'Android Remoting Tests': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'compile_targets': [
        'remoting_apk',
      ],
      'bot_type': 'builder_tester',
      'android_config': 'main_builder',
      'root_devices': True,
      'tests': [
        steps.AndroidInstrumentationTest(
            'ChromotingTest', 'remoting_test_apk',
            adb_install_apk=(
              'Chromoting.apk', 'org.chromium.chromoting')),
      ],
      'testing': {
        'platform': 'linux',
      },
    },
  },
}
