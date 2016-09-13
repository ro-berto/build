# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

RESULTS_URL = 'https://chromeperf.appspot.com'


KITCHEN_TEST_SPEC = {
  'chromium_config': 'chromium',
  'chromium_apply_config': [
    'mb',
    'ninja_confirm_noop',
    'archive_gpu_tests',
    'chrome_with_codecs'
  ],
  'gclient_config': 'chromium',
  'chromium_config_kwargs': {
    'BUILD_CONFIG': 'Release',
    'TARGET_BITS': 64,
  },
  'compile_targets': [
    'all',
  ],
  'testing': {
    'platform': 'linux',
  },
  'use_isolate': True,
  'enable_swarming': True,
}


SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-fyi-archive',
  },
  'builders': {
    'Chromium Mac 10.10 MacViews': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_apply_config': [
        'chromium_mac_mac_views',
        'mb',
        'force_mac_toolchain'
      ],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'checkout_dir': 'mac',
      'testing': {
        'platform': 'mac',
      },
    },
    'Chromium Mac 10.11': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'force_mac_toolchain'],
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
    'Chromium Mac 10.11 Force Mac Toolchain': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'force_mac_toolchain'],
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
    'Linux ARM': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_ARCH': 'arm',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
      'archive_build': True,
      'gs_bucket': 'chromium-fyi-archive',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'use_isolate': True,
      'enable_swarming': True,
      'swarming_dimensions': {
        'cpu': 'armv7l-32',
        'os': 'Ubuntu-14.04',
      },
    },
    'Linux V8 API Stability': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['v8_canary', 'with_branch_heads'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'all',
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    # There are no slaves for this builder and this builder doesn't
    # appear on the actual continuous waterfall; this configuration
    # is here so that a try bot can be added.
    'WebKit Linux slimming_paint_v2 Dummy Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb','ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'blink_tests',
      ],
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'tests': [
        steps.BlinkTest(extra_args=[
          '--additional-driver-flag=--enable-slimming-paint-v2',
        ]),
      ],
      'testing': {
          'platform': 'linux',
      },
      'enable_swarming': True,
      'use_isolate': True,
    },
    'WebKit Linux - WPTServe':{
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb','ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'blink_tests',
      ],
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'tests': [
        steps.BlinkTest(extra_args=[
          '--enable-wptserve',
        ]),
      ],
      'testing': {
          'platform': 'linux',
      },
      'enable_swarming': True,
      'use_isolate': True,
    },
    'WebKit Linux - TraceWrappables': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'blink_tests',
      ],
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'tests': [
        steps.BlinkTest(extra_args=[
          '--additional-driver-flag',
          '--enable-blink-features=TraceWrappables',
        ]),
      ],
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
      'use_isolate': True,
    },
    'WebKit Mac - WPTServe':{
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb','ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'blink_tests',
      ],
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'tests': [
        steps.BlinkTest(extra_args=[
          '--enable-wptserve',
        ]),
      ],
      'testing': {
          'platform': 'mac',
      },
      'enable_swarming': True,
      'use_isolate': True,
    },
    'WebKit Win - WPTServe':{
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb','ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'compile_targets': [
        'blink_tests',
      ],
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'tests': [
        steps.BlinkTest(extra_args=[
          '--enable-wptserve',
        ]),
      ],
      'testing': {
          'platform': 'win',
      },
      'enable_swarming': True,
      'use_isolate': True,
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
      'chromium_apply_config': ['force_mac_toolchain'],
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
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
    },
    'CFI Linux Full': {
      'chromium_config': 'chromium_cfi',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
    },
    'CFI Linux ToT': {
      'chromium_config': 'chromium_cfi',
      'chromium_apply_config': ['clang_tot', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
    },
    'CFI Linux CF': {
      'chromium_config': 'chromium_cfi',
      'chromium_apply_config': ['mb', 'clobber'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [ 'chromium_builder_asan' ],
      'cf_archive_build': True,
      'cf_gs_bucket': 'chromium-browser-cfi',
      'cf_gs_acl': 'public-read',
      'cf_archive_name': 'cfi',
      'testing': { 'platform': 'linux' },
    },
    'LTO Linux': {
      'chromium_config': 'chromium_official',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
    },
    'LTO Linux Perf': {
      'chromium_config': 'chromium_official',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [ 'chromium_builder_perf' ],
      'testing': {
        'platform': 'linux',
      },
    },
    'ThinLTO Linux ToT': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['clang_tot', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
    },
    'UBSanVptr Linux': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
    },
    'Mac OpenSSL': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['force_mac_toolchain'],
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
        steps.generate_isolated_script,
      ],
      'testing': {
        'platform': 'mac',
      },
    },
    'Site Isolation Linux': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
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
      'tests': [
        steps.BlinkTest(extra_args=[
          '--additional-driver-flag',
          '--site-per-process',
          '--additional-expectations',
          'src/third_party/WebKit/LayoutTests/FlagExpectations/site-per-process',
          '--options',
          'http/tests',
        ]),
      ],
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'checkout_dir': 'linux',
      'testing': {
        'platform': 'linux',
      },
    },
    'Site Isolation Win': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'win',
        'TARGET_BITS': 32,
      },
      'GYP_DEFINES': {
        'dcheck_always_on': '1',
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'content_unittests',
        'content_browsertests',
      ],
      'tests': [
        steps.BlinkTest(extra_args=[
          '--additional-driver-flag',
          '--site-per-process',
          '--additional-expectations',
          'src\\third_party\\WebKit\\LayoutTests\\FlagExpectations\\site-per-process',
        ]),
      ],
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'testing': {
        'platform': 'win',
      },
    },
    'Browser Side Navigation Linux': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
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
      'tests': [
        steps.BlinkTest(["--additional-driver-flag=--enable-browser-side-navigation"]),
      ],
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'CrWinClang': {
      'chromium_config': 'chromium_win_clang_official',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal'],
      'chromium_apply_config': ['mb'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'compile_targets': [
        'all',
      ],
      'bot_type': 'builder',
      'testing': {
        'platform': 'win',
      },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
      'checkout_dir': 'win_clang',
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
      'chromium_apply_config': ['mb'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'compile_targets': [
        'all',
      ],
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
      'checkout_dir': 'win_clang',
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
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'compile_targets': [
        'all',
      ],
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
      'chromium_apply_config': ['mb'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'all',
      ],
      'bot_type': 'builder',
      'testing': {
        'platform': 'win',
      },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
      'checkout_dir': 'win_clang',
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
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'all',
      ],
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
      'checkout_dir': 'win_clang',
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
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'all',
      ],
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
      'chromium_config': 'chromium_win_clang_tot',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'compile_targets': [
        'all',
      ],
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
    'CrWinClngLLDdbg': {
      'chromium_config': 'chromium_win_clang_tot',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'compile_targets': [
        'all',
      ],
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
    'CrWinClngLLDdbg tester': {
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
      'parent_buildername': 'CrWinClngLLDdbg',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'CrWinClangLLD64': {
      'chromium_config': 'chromium_win_clang_tot',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'all',
      ],
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
    'CrWinClangLLD64 tester': {
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
      'parent_buildername': 'CrWinClangLLD64',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'CrWinClngLLD64dbg': {
      'chromium_config': 'chromium_win_clang_tot',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'all',
      ],
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
    'CrWinClngLLD64dbg tester': {
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
      'parent_buildername': 'CrWinClngLLD64dbg',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'CrWinAsan': {
      'chromium_config': 'chromium_win_clang_asan_tot',
      'chromium_apply_config': ['mb', 'clobber'],
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
      'compile_targets': [ 'chromium_builder_asan' ],
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
      'chromium_config': 'chromium_win_clang_asan_tot',
      'chromium_apply_config': ['mb', 'clobber'],
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
      'compile_targets': [ 'chromium_builder_asan' ],
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
    'CrWinAsanCov': {
      'chromium_config': 'chromium_win_clang_asan_tot_coverage',
      'chromium_apply_config': ['mb', 'clobber'],
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
      'compile_targets': [ 'chromium_builder_asan' ],
      # add_tests_as_compile_targets not needed for the asan bot, it doesn't
      # build everything.
    },
    'CrWinAsanCov tester': {
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
      'parent_buildername': 'CrWinAsanCov',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'CrWinGoma': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary', 'mb'],
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
      'chromium_apply_config': ['goma_canary','mb', 'shared_library'],
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
      'chromium_apply_config': ['goma_canary', 'mb'],
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
      'chromium_apply_config': ['goma_canary', 'mb', 'shared_library'],
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
      'chromium_apply_config': ['goma_canary', 'mb'],
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
      'chromium_apply_config': ['clobber', 'goma_canary', 'mb',
                                'shared_library'],
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
      'chromium_config': 'chromium_win_clang_official',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['goma_canary', 'mb'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'compile_targets': [
        'all',
      ],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'win',
      },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,

      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
    },
    'Chromium Linux Goma Canary': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary', 'mb'],
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
      'chromium_apply_config': ['clobber', 'goma_canary', 'mb'],
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
    'Chromium Linux Precise Goma LinkTest': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary', 'goma_linktest', 'mb'],
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
    'Chromium Mac 10.9 Goma Canary': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary', 'mb', 'force_mac_toolchain'],
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
    'Chromium Mac 10.9 Goma Canary (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary', 'mb', 'force_mac_toolchain'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'compile_targets': [ 'chromium_builder_tests' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'testing': {
        'platform': 'mac'
      }
    },
    'Chromium Mac 10.9 Goma Canary (clobber)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'clobber',
        'goma_canary',
        'mb',
        'force_mac_toolchain',
      ],
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
    'Chromium Mac 10.9 Goma Canary (dbg)(clobber)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'clobber',
        'goma_canary',
        'mb',
        'force_mac_toolchain',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
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
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'GYP_DEFINES': {
        'component': 'shared_library',

        # Enable debug info, as on official builders, to catch issues with
        # optimized debug info.
        'linux_dump_symbols': '1',
      },
      'compile_targets': [
        'all',
      ],
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
        steps.generate_isolated_script,
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
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'all',
      ],
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
      'chromium_apply_config': ['mb', 'lsan'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'all',
      ],
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
        steps.generate_isolated_script,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'ClangToTLinuxASan',
      'testing': { 'platform': 'linux', },
      'enable_swarming': True,
    },
    'ClangToTLinuxLLD': {
      'chromium_config': 'clang_tot_linux_lld',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'all',
      ],
      'bot_type': 'builder',
      'testing': { 'platform': 'linux', },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ClangToTLinuxLLD tester': {
      'chromium_config': 'chromium_no_goma',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'ClangToTLinuxLLD',
      'testing': { 'platform': 'linux', },
      'enable_swarming': True,
    },
    'ClangToTLinuxUBSanVptr': {
      'chromium_config': 'clang_tot_linux_ubsan_vptr',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'all',
      ],
      'bot_type': 'builder',
      'testing': { 'platform': 'linux', },
      'tests': {
        steps.SizesStep(RESULTS_URL, 'ClangToTLinuxUBSanVptr')
      },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ClangToTLinuxUBSanVptr tester': {
      'chromium_config': 'chromium_no_goma',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'ClangToTLinuxUBSanVptr',
      'testing': { 'platform': 'linux', },
      'enable_swarming': True,
    },
    'ClangToTAndroidASan': {
      'chromium_config': 'clang_tot_android_asan',
      'chromium_apply_config': ['mb'],
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
      },
      'compile_targets': [
        'all',
      ],
      'bot_type': 'builder_tester',
      'android_config': 'clang_asan_tot_release_builder',
      'testing': { 'platform': 'linux', },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
      'root_devices': True,
      'test_generators': [
        steps.generate_gtest,
        steps.generate_junit_test,
      ],
    },
    'ClangToTMac': {
      'chromium_config': 'clang_tot_mac',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'GYP_DEFINES': {
        'component': 'shared_library',
      },
      'compile_targets': [
        'all',
      ],
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
        steps.generate_isolated_script,
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
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'all',
      ],
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
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'all',
      ],
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
        steps.generate_isolated_script,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'ClangToTMacASan',
      'testing': { 'platform': 'mac', },
      'enable_swarming': True,
    },
    'ClangToTWin': {
      'chromium_config': 'chromium_win_clang_official_tot',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'compile_targets': [
        'all',
      ],
      'bot_type': 'builder',
      'testing': { 'platform': 'win', },
      'tests': { steps.SizesStep(RESULTS_URL, 'ClangToTWin') },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ClangToTWin tester': {
      'chromium_config': 'chromium_no_goma',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'test_generators': [steps.generate_gtest],
      'bot_type': 'tester',
      'parent_buildername': 'ClangToTWin',
      'testing': { 'platform': 'win' },
      'enable_swarming': True,
    },
    'ClangToTWin(dbg)': {
      'chromium_config': 'chromium_win_clang_tot',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'compile_targets': [
        'all',
      ],
      'bot_type': 'builder',
      'testing': { 'platform': 'win', },
      'tests': { steps.SizesStep(RESULTS_URL, 'ClangToTWin(dbg)') },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ClangToTWin(dbg) tester': {
      'chromium_config': 'chromium_no_goma',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'test_generators': [steps.generate_gtest],
      'bot_type': 'tester',
      'parent_buildername': 'ClangToTWin(dbg)',
      'testing': { 'platform': 'win' },
      'enable_swarming': True,
    },
    'ClangToTWin(dll)': {
      'chromium_config': 'chromium_win_clang_tot',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'compile_targets': [
        'all',
      ],
      'GYP_DEFINES': { 'component': 'shared_library' },
      'bot_type': 'builder',
      'testing': { 'platform': 'win', },
      'tests': { steps.SizesStep(RESULTS_URL, 'ClangToTWin(dll)') },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ClangToTWin(dll) tester': {
      'chromium_config': 'chromium_no_goma',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'test_generators': [steps.generate_gtest],
      'bot_type': 'tester',
      'parent_buildername': 'ClangToTWin(dll)',
      'testing': { 'platform': 'win' },
      'enable_swarming': True,
    },
    'ClangToTWin64': {
      'chromium_config': 'chromium_win_clang_official_tot',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'all',
      ],
      'bot_type': 'builder',
      'testing': { 'platform': 'win', },
      'tests': { steps.SizesStep(RESULTS_URL, 'ClangToTWin64') },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ClangToTWin64 tester': {
      'chromium_config': 'chromium_no_goma',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_generators': [steps.generate_gtest],
      'bot_type': 'tester',
      'parent_buildername': 'ClangToTWin64',
      'testing': { 'platform': 'win' },
      'enable_swarming': True,
    },
    'ClangToTWin64(dbg)': {
      'chromium_config': 'chromium_win_clang_tot',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'all',
      ],
      'bot_type': 'builder',
      'testing': { 'platform': 'win', },
      'tests': { steps.SizesStep(RESULTS_URL, 'ClangToTWin64(dbg)') },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ClangToTWin64(dbg) tester': {
      'chromium_config': 'chromium_no_goma',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'test_generators': [steps.generate_gtest],
      'bot_type': 'tester',
      'parent_buildername': 'ClangToTWin64(dbg)',
      'testing': { 'platform': 'win' },
      'enable_swarming': True,
    },
    'ClangToTWin64(dll)': {
      'chromium_config': 'chromium_win_clang_tot',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'all',
      ],
      'GYP_DEFINES': { 'component': 'shared_library' },
      'bot_type': 'builder',
      'testing': { 'platform': 'win', },
      'tests': { steps.SizesStep(RESULTS_URL, 'ClangToTWin64(dll)') },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ClangToTWin64(dll) tester': {
      'chromium_config': 'chromium_no_goma',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_generators': [steps.generate_gtest],
      'bot_type': 'tester',
      'parent_buildername': 'ClangToTWin64(dll)',
      'testing': { 'platform': 'win' },
      'enable_swarming': True,
    },
    'Win Builder (ANGLE)': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['angle_top_of_tree'],
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
      'patch_root': 'src/third_party/angle',
      'enable_swarming': True,
      'use_isolate': True,
    },
    'Win7 Tests (ANGLE)': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'parent_buildername': 'Win Builder (ANGLE)',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
      'use_isolate': True,
    },

    'Headless Linux (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'linux',
      },
      'bot_type': 'builder_tester',
      'test_generators': [
        steps.generate_gtest,
      ],
      'testing': {
        'platform': 'linux',
      },
    },

    'Android Builder (dbg)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['chrome_with_codecs', 'mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder',
      'bot_type': 'builder',
      'compile_targets': [
        'chromedriver_webview_shell_apk',
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
      'android_config': 'non_device_wipe_provisioning',
      'root_devices': True,
      'tests': [
        steps.GTestTest('gfx_unittests'),
      ],
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
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
      'parent_buildername': 'Android Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder',
      'root_devices': True,
      'enable_swarming': False,
      'tests': [
        steps.GTestTest('remoting_unittests'),
        steps.AndroidInstrumentationTest('ChromotingTest'),
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Android Find Annotated Test': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder_mb',
      'remove_system_webview': True,
      'tests': [
        steps.FindAnnotatedTest(),
      ],
      'testing': {
        'platform': 'linux',
      },
    },


    'Android Asan Builder Tests (dbg)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'builder_tester',
      'android_config': 'clang_tests',
      'root_devices': True,
      'tests': [
        steps.AndroidInstrumentationTest('AndroidWebViewTest', tool='asan'),
        steps.AndroidInstrumentationTest('ChromePublicTest', tool='asan'),
        steps.AndroidInstrumentationTest('ContentShellTest', tool='asan'),
        steps.AndroidInstrumentationTest('ChromeSyncShellTest', tool='asan'),
      ],
      'test_generators': [
        steps.generate_gtest,
        steps.generate_instrumentation_test,
        steps.generate_isolated_script,
        steps.generate_script,
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Win 10 Fast Ring': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'GYP_DEFINES': {
        'dcheck_always_on': '1',
      },
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'testing': {
        'platform': 'win',
      },
    },
    'Android Coverage (dbg)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'tester',
      'parent_buildername': 'Android Builder (dbg)',
      'android_config': 'incremental_coverage_builder_tests',
      'root_devices': True,
      'checkout_dir': 'android',
      'tests': [
        steps.AndroidInstrumentationTest('AndroidWebViewTest'),
        steps.AndroidInstrumentationTest('ChromePublicTest'),
        steps.AndroidInstrumentationTest('ContentShellTest'),
        steps.AndroidInstrumentationTest('ChromeSyncShellTest'),
        steps.IncrementalCoverageTest(),
      ],
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'Android Cloud Tests': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'builder_tester',
      'android_config': 'x86_builder_mb',
      'tests': [],
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
        steps.generate_instrumentation_test,
      ],
      'testing': {
        'platform': 'linux',
      },
      'use_isolate': True,
      'enable_swarming': True,
    },
    'Win SyzyAsan (rel)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
          'mb',
          'syzyasan_compile_only',
          'shared_library',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'win',
        'TARGET_BITS': 32,
      },
      'compile_targets': [
        'chrome',
      ],
      'enable_swarming': True,
      'checkout_dir': 'win',
      'testing': {
        'platform': 'win',
      },
    },
    'Android VR Tests': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'tester',
      'parent_buildername': 'Android Builder (dbg)',
      'android_config': 'main_builder_mb',
      'root_devices': True,
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
        steps.generate_instrumentation_test,
      ],
      'testing': {
        'platform': 'linux',
      },
    },

    'Linux remote_run Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
        'ninja_confirm_noop',
        'archive_gpu_tests',
        'chrome_with_codecs'
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
      'use_isolate': True,
      'enable_swarming': True,
    },
    'Linux remote_run Tester': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
        'ninja_confirm_noop',
        'archive_gpu_tests',
        'chrome_with_codecs'
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'Linux remote_run Builder',
      'tests': [
        steps.GTestTest('base_unittests'),
      ],
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
        steps.generate_instrumentation_test,
      ],
      'testing': {
        'platform': 'linux',
      },
      'use_isolate': True,
      'enable_swarming': True,
    },
    'Mojo ChromiumOS': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['chromeos', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'chromeos',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'testing': { 'platform': 'linux', },
      'use_isolate': True,
      'enable_swarming': True,
    },
    'Mojo Windows': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'win',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder_tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'testing': { 'platform': 'win', },
      'use_isolate': True,
      'enable_swarming': True,
    },
  },
}
