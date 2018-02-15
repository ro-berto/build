# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

RESULTS_URL = 'https://chromeperf.appspot.com'


def config(name,
           android_config=None,
           build_config='Release',
           chromium_config='clang_tot_linux',
           ninja_confirm_noop=True,
           is_msan=False,
           target_arch='intel',
           target_bits=64):
  cfg = {
    'chromium_config': chromium_config,
    'chromium_apply_config': [
      'mb',
    ],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': build_config,
      'TARGET_ARCH': target_arch,
      'TARGET_BITS': target_bits,
    },
    'bot_type': 'builder_tester',
    'test_results_config': 'staging_server',
    'testing': {
      'platform': 'linux',
    },
    'tests': {
      steps.SizesStep(RESULTS_URL, name)
    },

    # TODO(dpranke): Get rid of this flag, it's a misfeature. This was
    # added to allow the bots to run `ninja` instead of `ninja all`
    # or `ninja all base_unittests net_unittests...`, but really the
    # compile() call in the recipe should be smart enough to do this
    # automatically. This shouldn't be configurable per bot.
    'add_tests_as_compile_targets': False,
  }

  if android_config:
      cfg['android_config'] = android_config
      cfg['chromium_config_kwargs']['TARGET_PLATFORM'] = 'android'
      cfg['gclient_apply_config'] = ['android']

  if ninja_confirm_noop:
      cfg['chromium_apply_config'].append('ninja_confirm_noop')

  if is_msan:
      cfg['chromium_apply_config'].append('prebuilt_instrumented_libraries')

  return name, cfg


SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-clang-archive',
  },
  'builders': {
    'CFI Linux ToT': {
      'chromium_config': 'clang_tot_linux',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
    },
    'CFI Linux CF': {
      'chromium_config': 'chromium',
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
      'test_results_config': 'staging_server',
      'testing': { 'platform': 'linux' },
    },
    'CFI Linux (icall)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'testing': {'platform': 'linux'},
    },
    'UBSanVptr Linux': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
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
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
      'checkout_dir': 'win',
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
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
      'checkout_dir': 'win',
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
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
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
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
      'checkout_dir': 'win',
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
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
      'checkout_dir': 'win',
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
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'CrWinClangLLD': {
      'chromium_config': 'chromium_win_clang_tot',
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
      'GYP_DEFINES': { 'component': 'shared_library', 'use_lld': 1 },
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
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
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
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
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
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
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ToTWinCFI': {
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
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ToTWinCFI64': {
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
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ToTWinThinLTO64': {
      'chromium_config': 'chromium_win_clang_tot',
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
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
      'tests': {
        steps.SizesStep(RESULTS_URL, 'ToTWinThinLTO64')
      },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'CrWinAsan': {
      'chromium_config': 'chromium_win_clang_asan_tot',
      'chromium_apply_config': ['mb', 'clobber'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
      'compile_targets': [ 'chromium_builder_asan' ],
      # add_tests_as_compile_targets not needed for the asan bot, it doesn't
      # build everything.
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
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
      'compile_targets': [ 'chromium_builder_asan' ],
      # add_tests_as_compile_targets not needed for the asan bot, it doesn't
      # build everything.
    },
    'CrWinAsanCov': {
      'chromium_config': 'chromium_win_clang_asan_tot_coverage',
      'chromium_apply_config': ['mb', 'clobber'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
      'compile_targets': [ 'chromium_builder_asan' ],
      # add_tests_as_compile_targets not needed for the asan bot, it doesn't
      # build everything.
    },
    'ToTAndroidASan': {
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
      'test_results_config': 'staging_server',
      'testing': { 'platform': 'linux', },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
      'root_devices': True,
    },
    'ToTAndroid (dbg)': {
      'chromium_config': 'clang_tot_android_dbg',
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
      'android_config': 'clang_tot_debug_builder',
      'test_results_config': 'staging_server',
      'testing': { 'platform': 'linux', },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ToTAndroid x64': {
      'chromium_config': 'clang_tot_android',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android',
      },
      'compile_targets': [
        'all',
      ],
      'bot_type': 'builder_tester',
      'android_config': 'clang_builder_mb_x64',
      'test_results_config': 'staging_server',
      'testing': { 'platform': 'linux', },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ToTMac': {
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
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': { 'platform': 'mac', },
      'tests': {
        steps.SizesStep(RESULTS_URL, 'ToTMac')
      },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ToTMac (dbg)': {
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
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': { 'platform': 'mac', },
      'tests': {
        steps.SizesStep(RESULTS_URL, 'ToTMac (dbg)')
      },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ToTMacASan': {
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
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': { 'platform': 'mac', },
      'tests': {
        steps.SizesStep(RESULTS_URL, 'ToTMacASan')
      },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ToTWin': {
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
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': { 'platform': 'win', },
      'tests': { steps.SizesStep(RESULTS_URL, 'ToTWin') },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ToTWin(dbg)': {
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
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': { 'platform': 'win', },
      'tests': { steps.SizesStep(RESULTS_URL, 'ToTWin(dbg)') },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ToTWin(dll)': {
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
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': { 'platform': 'win', },
      'tests': { steps.SizesStep(RESULTS_URL, 'ToTWin(dll)') },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ToTWin64': {
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
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': { 'platform': 'win', },
      'tests': { steps.SizesStep(RESULTS_URL, 'ToTWin64') },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ToTWinLibcxx64': {
      'chromium_config': 'chromium_win_clang_official_tot',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'all',
      ],
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': { 'platform': 'win', },
      'tests': { steps.SizesStep(RESULTS_URL, 'ToTWinLibcxx64') },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ToTWin64(dbg)': {
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
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': { 'platform': 'win', },
      'tests': { steps.SizesStep(RESULTS_URL, 'ToTWin64(dbg)') },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'ToTWin64(dll)': {
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
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': { 'platform': 'win', },
      'tests': { steps.SizesStep(RESULTS_URL, 'ToTWin64(dll)') },
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
  },
}


SPEC['builders'].update([
    config('ToTAndroid',
           android_config='clang_tot_release_builder',
           chromium_config='clang_tot_android',
           ninja_confirm_noop=False,
           target_arch='arm',
           target_bits=32),

    config('ToTAndroid64',
           android_config='clang_tot_release_builder',
           chromium_config='clang_tot_android',
           ninja_confirm_noop=False,
           target_arch='arm',
           target_bits=64),

    config('ToTAndroidCFI',
           android_config='clang_tot_release_builder',
           chromium_config='clang_tot_android',
           ninja_confirm_noop=False,
           target_arch='arm',
           target_bits=32),

    config('ToTLinux'),

    config('ToTLinux (dbg)',
           build_config='Debug'),

    config('ToTLinuxASan',
           chromium_config='clang_tot_linux_asan'),

    config('ToTLinuxASanLibfuzzer',
           chromium_config='clang_tot_linux_asan'),

    config('ToTLinuxMSan',
           is_msan=True),

    config('ToTLinuxThinLTO'),

    config('ToTLinuxUBSanVptr',
           chromium_config='clang_tot_linux_ubsan_vptr'),
])
