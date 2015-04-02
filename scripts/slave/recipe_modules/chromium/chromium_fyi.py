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
      'recipe_config': 'chromium',
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
    'Cast Linux': {
      'recipe_config': 'cast_linux',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Cast Android (dbg)': {
      'recipe_config': 'chromium_android',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'cast_builder',
      'testing': {
        'platform': 'linux',
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
      'recipe_config': 'chromium_blink_merged',
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
      'recipe_config': 'chromium_win_clang_official',
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
      'enable_swarming': True,
    },
    'CrWinClang(dbg)': {
      'recipe_config': 'chromium_win_clang',
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
      'recipe_config': 'chromium_no_goma',
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
      'recipe_config': 'chromium_win_clang',
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
      'recipe_config': 'chromium_no_goma',
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
      'recipe_config': 'chromium_win_clang_official',
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
      'recipe_config': 'chromium_no_goma',
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
      'recipe_config': 'chromium_win_clang',
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
      'recipe_config': 'chromium_no_goma',
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
      'recipe_config': 'chromium_win_clang',
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
      'recipe_config': 'chromium_no_goma',
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
      'recipe_config': 'chromium_win_clang',
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
      'recipe_config': 'chromium_no_goma',
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
      'recipe_config': 'chromium_win_clang_asan',
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
      'recipe_config': 'chromium_win_asan',
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
      'recipe_config': 'chromium_win_clang_asan',
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
      'recipe_config': 'chromium_win_asan',
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
      'recipe_config': 'chromium_win_goma_canary',
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
      'recipe_config': 'chromium_win_goma_canary_dll',
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
      'recipe_config': 'chromium_win_goma_canary',
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
      'recipe_config': 'chromium_win_goma_canary_dll',
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
      'recipe_config': 'chromium_win_goma_canary',
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
      'recipe_config': 'chromium_win_goma_canary_clobber',
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
      'recipe_config': 'chromium_win_goma_canary_clang',
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
      'recipe_config': 'chromium_linux_goma_canary',
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
      'recipe_config': 'chromium_linux_goma_canary_clobber',
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
      'recipe_config': 'chromium_linux_goma_canary_clobber',
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
      'recipe_config': 'chromium_linux_goma_canary_linktest',
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
      'recipe_config': 'chromium_mac_goma_canary',
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
      'recipe_config': 'chromium_mac_goma_canary',
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
      'recipe_config': 'chromium_mac_goma_canary_clobber',
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
      'recipe_config': 'chromium_mac_goma_canary_clobber',
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
      'recipe_config': 'clang_tot_linux',
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
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ClangToTLinux tester': {
      'recipe_config': 'chromium_no_goma',
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
      'recipe_config': 'clang_tot_linux',
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
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ClangToTLinuxASan': {
      'recipe_config': 'clang_tot_linux_asan',
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
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ClangToTLinuxASan tester': {
      'recipe_config': 'chromium_linux_asan',
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
      'recipe_config': 'clang_tot_android_asan',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
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
      'testing': { 'platform': 'linux', },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'Linux Builder (clobber)': {
      'recipe_config': 'chromium',
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
  },
}
