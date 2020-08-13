# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_spec, steps

RESULTS_URL = 'https://chromeperf.appspot.com'


def _chromium_clang_spec(**kwargs):
  return bot_spec.BotSpec.create(
      build_gs_bucket='chromium-clang-archive', **kwargs)


def config(name,
           android_config=None,
           build_config='Release',
           chromium_config='clang_tot_linux',
           target_arch='intel',
           target_bits=64,
           official=False):
  cfg = {
      'chromium_config': chromium_config,
      'chromium_apply_config': ['mb'],
      'chromium_tests_apply_config': ['use_swarming_command_lines'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['clang_tot'],
      'chromium_config_kwargs': {
          'BUILD_CONFIG': build_config,
          'TARGET_ARCH': target_arch,
          'TARGET_BITS': target_bits,
      },
      'execution_mode': bot_spec.COMPILE_AND_TEST,
      'test_results_config': 'staging_server',
      'test_specs': {
          bot_spec.TestSpec.create(steps.SizesStep, RESULTS_URL, name)
      },
      'simulation_platform': 'linux',
  }

  if android_config:
    cfg['android_config'] = android_config
    cfg['chromium_config_kwargs']['TARGET_PLATFORM'] = 'android'
    cfg['gclient_apply_config'].append('android')

  if official:
    cfg['gclient_apply_config'].append('chrome_internal')
    cfg['gclient_apply_config'].append('checkout_pgo_profiles')
    cfg['swarming_server'] = 'https://chrome-swarming.appspot.com'
    cfg['isolate_server'] = 'https://chrome-isolated.appspot.com'
    cfg['swarming_dimensions'] = {
        'pool': 'chrome.tests',
        'os': 'Ubuntu-14.04',
    }
  else:
    cfg['isolate_server'] = 'https://isolateserver.appspot.com'

  return name, _chromium_clang_spec(**cfg)


SPEC = {
    'CFI Linux ToT':
        _chromium_clang_spec(
            chromium_config='clang_tot_linux',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['clang_tot'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    'CFI Linux CF':
        _chromium_clang_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            # Not a ToT bot so no clang_tot gclient_apply_config.
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            compile_targets=['chromium_builder_asan'],
            cf_archive_build=True,
            cf_gs_bucket='chromium-browser-cfi',
            cf_gs_acl='public-read',
            cf_archive_name='cfi',
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    'UBSanVptr Linux':
        _chromium_clang_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            # Not a ToT bot so no clang_tot gclient_apply_config.
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    'linux-win_cross-rel':
        _chromium_clang_spec(
            chromium_config='chromium_win_clang_tot',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['clang_tot', 'win'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'win',
            },
            compile_targets=[
                'all',
            ],
            test_results_config='staging_server',
            simulation_platform='win',
        ),
    'ToTiOS':
        _chromium_clang_spec(
            chromium_config='chromium_no_goma',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='ios',
            gclient_apply_config=['clang_tot'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
            },
            simulation_platform='mac',
        ),
    'ToTiOSDevice':
        _chromium_clang_spec(
            chromium_config='chromium_no_goma',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='ios',
            gclient_apply_config=['clang_tot'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
            },
            simulation_platform='mac',
        ),
    'ToTWinCFI':
        _chromium_clang_spec(
            chromium_config='chromium_win_clang_tot',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['clang_tot'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            compile_targets=[
                'all',
            ],
            test_results_config='staging_server',
            simulation_platform='win',
        ),
    'ToTWinCFI64':
        _chromium_clang_spec(
            chromium_config='chromium_win_clang_tot',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['clang_tot'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            compile_targets=[
                'all',
            ],
            test_results_config='staging_server',
            simulation_platform='win',
        ),
    'ToTWinOfficial':
        _chromium_clang_spec(
            chromium_config='chromium_win_clang_tot',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            gclient_config='chromium',
            gclient_apply_config=[
                'clang_tot', 'chrome_internal', 'checkout_pgo_profiles'
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            compile_targets=[
                'all',
            ],
            test_results_config='staging_server',
            simulation_platform='win',
            test_specs=[
                bot_spec.TestSpec.create(steps.SizesStep, RESULTS_URL,
                                         'ToTWinOfficial')
            ],
            swarming_server='https://chrome-swarming.appspot.com',
            isolate_server='https://chrome-isolated.appspot.com',
            swarming_dimensions={
                'pool': 'chrome.tests',
                'os': 'Windows-10',
            },
        ),
    'ToTWinThinLTO64':
        _chromium_clang_spec(
            chromium_config='chromium_win_clang_tot',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            gclient_config='chromium',
            gclient_apply_config=[
                'clang_tot', 'chrome_internal', 'checkout_pgo_profiles'
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            compile_targets=[
                'all',
            ],
            test_results_config='staging_server',
            simulation_platform='win',
            test_specs=[
                bot_spec.TestSpec.create(steps.SizesStep, RESULTS_URL,
                                         'ToTWinThinLTO64')
            ],
            swarming_server='https://chrome-swarming.appspot.com',
            isolate_server='https://chrome-isolated.appspot.com',
            swarming_dimensions={
                'pool': 'chrome.tests',
                'os': 'Windows-10',
            },
        ),
    'CrWinAsan':
        _chromium_clang_spec(
            chromium_config='chromium_win_clang_asan_tot',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['clang_tot'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            test_results_config='staging_server',
            simulation_platform='win',
            compile_targets=['chromium_builder_asan'],
        ),
    'CrWinAsan(dll)':
        _chromium_clang_spec(
            chromium_config='chromium_win_clang_asan_tot',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['clang_tot'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            test_results_config='staging_server',
            simulation_platform='win',
            compile_targets=['chromium_builder_asan'],
        ),
    'ToTAndroidASan':
        _chromium_clang_spec(
            chromium_config='clang_tot_android_asan',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['clang_tot', 'android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 32,
            },
            compile_targets=[
                'all',
            ],
            android_config='clang_asan_tot_release_builder',
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    'ToTAndroid (dbg)':
        _chromium_clang_spec(
            chromium_config='clang_tot_android_dbg',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['clang_tot', 'android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 32,
            },
            compile_targets=[
                'all',
            ],
            android_config='clang_tot_debug_builder',
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    'ToTAndroid x64':
        _chromium_clang_spec(
            chromium_config='clang_tot_android',
            gclient_config='chromium',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_apply_config=['clang_tot', 'android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            compile_targets=[
                'all',
            ],
            android_config='clang_builder_mb_x64',
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    'ToTMac':
        _chromium_clang_spec(
            chromium_config='clang_tot_mac',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['clang_tot'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            compile_targets=[
                'all',
            ],
            test_results_config='staging_server',
            simulation_platform='mac',
            test_specs={
                bot_spec.TestSpec.create(steps.SizesStep, RESULTS_URL, 'ToTMac')
            },
        ),
    'ToTMacOfficial':
        _chromium_clang_spec(
            chromium_config='clang_tot_mac',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            gclient_config='chromium',
            gclient_apply_config=[
                'clang_tot', 'chrome_internal', 'checkout_pgo_profiles'
            ],
            swarming_server='https://chrome-swarming.appspot.com',
            isolate_server='https://chrome-isolated.appspot.com',
            # Run with lower priority; see https://crbug.com/937297#c26
            swarming_default_priority=210,
            swarming_dimensions={
                'gpu': None,
                'pool': 'chrome.tests',
            },
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            compile_targets=[
                'all',
            ],
            test_results_config='staging_server',
            simulation_platform='mac',
            test_specs={
                bot_spec.TestSpec.create(steps.SizesStep, RESULTS_URL,
                                         'ToTMacOfficial')
            },
        ),
    'ToTMac (dbg)':
        _chromium_clang_spec(
            chromium_config='clang_tot_mac',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['clang_tot'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            compile_targets=[
                'all',
            ],
            test_results_config='staging_server',
            simulation_platform='mac',
            test_specs={
                bot_spec.TestSpec.create(steps.SizesStep, RESULTS_URL,
                                         'ToTMac (dbg)')
            },
        ),
    'ToTMacASan':
        _chromium_clang_spec(
            chromium_config='clang_tot_mac_asan',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['clang_tot'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            compile_targets=[
                'all',
            ],
            test_results_config='staging_server',
            simulation_platform='mac',
        ),
    'ToTWin':
        _chromium_clang_spec(
            chromium_config='chromium_win_clang_official_tot',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            gclient_config='chromium',
            gclient_apply_config=[
                'clang_tot', 'chrome_internal', 'checkout_pgo_profiles'
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            compile_targets=[
                'all',
            ],
            test_results_config='staging_server',
            simulation_platform='win',
            test_specs=[
                bot_spec.TestSpec.create(steps.SizesStep, RESULTS_URL,
                                         'ToTWin'),
            ],
            swarming_server='https://chrome-swarming.appspot.com',
            isolate_server='https://chrome-isolated.appspot.com',
            swarming_dimensions={
                'pool': 'chrome.tests',
                'os': 'Windows-10',
            },
        ),
    'ToTWin(dbg)':
        _chromium_clang_spec(
            chromium_config='chromium_win_clang_tot',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['clang_tot'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
            },
            compile_targets=[
                'all',
            ],
            test_results_config='staging_server',
            simulation_platform='win',
            test_specs=[
                bot_spec.TestSpec.create(steps.SizesStep, RESULTS_URL,
                                         'ToTWin(dbg)'),
            ],
        ),
    'ToTWin(dll)':
        _chromium_clang_spec(
            chromium_config='chromium_win_clang_tot',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['clang_tot'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            compile_targets=[
                'all',
            ],
            test_results_config='staging_server',
            simulation_platform='win',
            test_specs=[
                bot_spec.TestSpec.create(steps.SizesStep, RESULTS_URL,
                                         'ToTWin(dll)'),
            ],
        ),
    'ToTWin64':
        _chromium_clang_spec(
            chromium_config='chromium_win_clang_official_tot',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            gclient_config='chromium',
            gclient_apply_config=[
                'clang_tot', 'chrome_internal', 'checkout_pgo_profiles'
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            compile_targets=[
                'all',
            ],
            test_results_config='staging_server',
            simulation_platform='win',
            test_specs=[
                bot_spec.TestSpec.create(steps.SizesStep, RESULTS_URL,
                                         'ToTWin64'),
            ],
            swarming_server='https://chrome-swarming.appspot.com',
            isolate_server='https://chrome-isolated.appspot.com',
            swarming_dimensions={
                'pool': 'chrome.tests',
                'os': 'Windows-10',
            },
        ),
    'ToTWinASanLibfuzzer':
        _chromium_clang_spec(
            chromium_config='chromium_win_clang_asan_tot',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['clang_tot'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            compile_targets=[
                'all',
            ],
            test_results_config='staging_server',
            simulation_platform='win',
        ),
    'ToTWin64(dbg)':
        _chromium_clang_spec(
            chromium_config='chromium_win_clang_tot',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['clang_tot'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            compile_targets=[
                'all',
            ],
            test_results_config='staging_server',
            simulation_platform='win',
            test_specs=[
                bot_spec.TestSpec.create(steps.SizesStep, RESULTS_URL,
                                         'ToTWin64(dbg)'),
            ],
        ),
    'ToTWin64(dll)':
        _chromium_clang_spec(
            chromium_config='chromium_win_clang_tot',
            chromium_apply_config=['mb'],
            chromium_tests_apply_config=['use_swarming_command_lines'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['clang_tot'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            compile_targets=[
                'all',
            ],
            test_results_config='staging_server',
            simulation_platform='win',
            test_specs=[
                bot_spec.TestSpec.create(steps.SizesStep, RESULTS_URL,
                                         'ToTWin64(dll)'),
            ],
        ),
}

SPEC.update([
    config(
        'ToTAndroid',
        android_config='clang_tot_release_builder',
        chromium_config='clang_tot_android',
        target_arch='arm',
        target_bits=32),
    config(
        'ToTAndroid64',
        android_config='clang_tot_release_builder',
        chromium_config='clang_tot_android',
        target_arch='arm',
        target_bits=64),
    config(
        'ToTAndroidCFI',
        android_config='clang_tot_release_builder',
        chromium_config='clang_tot_android',
        target_arch='arm',
        target_bits=32),
    config(
        'ToTAndroidOfficial',
        android_config='clang_tot_release_builder',
        chromium_config='clang_tot_android',
        target_arch='arm',
        target_bits=32),
    config('ToTLinux'),
    config('ToTLinuxOfficial', official=True),
    config('ToTLinux (dbg)', build_config='Debug'),
    config('ToTLinuxASan', chromium_config='clang_tot_linux_asan'),
    config('ToTLinuxASanLibfuzzer', chromium_config='clang_tot_linux_asan'),
    config('ToTLinuxMSan'),
    config('ToTLinuxTSan'),
    config('ToTLinuxThinLTO'),
    config('ToTLinuxUBSanVptr', chromium_config='clang_tot_linux_ubsan_vptr'),
])
