# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import bot_spec
from . import steps

RESULTS_URL = 'https://chromeperf.appspot.com'


def config(name,
           android_config=None,
           build_config='Release',
           chromium_config='clang_tot_linux',
           target_arch='intel',
           target_bits=64,
           official=False):
  cfg = {
      'chromium_config': chromium_config,
      'chromium_apply_config': ['mb', 'mb_luci_auth'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['clang_tot'],
      'chromium_config_kwargs': {
          'BUILD_CONFIG': build_config,
          'TARGET_ARCH': target_arch,
          'TARGET_BITS': target_bits,
      },
      'bot_type': bot_spec.BUILDER_TESTER,
      'test_results_config': 'staging_server',
      'testing': {
          'platform': 'linux',
      },
      'tests': {steps.SizesStep(RESULTS_URL, name)},

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
    cfg['gclient_apply_config'].append('android')

  if official:
    cfg['gclient_apply_config'].append('chrome_internal')
    cfg['swarming_server'] = 'https://chrome-swarming.appspot.com'
    cfg['isolate_server'] = 'https://chrome-isolated.appspot.com'
    cfg['swarming_dimensions'] = {
        'pool': 'chrome.tests.template',
        'os': 'Ubuntu-14.04',
    }

  return name, bot_spec.BotSpec.create(**cfg)


SPEC = {
    'settings': {
        'build_gs_bucket': 'chromium-clang-archive',
    },
    'builders': {
        'CFI Linux ToT':
            bot_spec.BotSpec.create(
                chromium_config='clang_tot_linux',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['clang_tot'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER_TESTER,
                test_results_config='staging_server',
                testing={
                    'platform': 'linux',
                },
            ),
        'CFI Linux CF':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                # Not a ToT bot so no clang_tot gclient_apply_config.
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                compile_targets=['chromium_builder_asan'],
                cf_archive_build=True,
                cf_gs_bucket='chromium-browser-cfi',
                cf_gs_acl='public-read',
                cf_archive_name='cfi',
                test_results_config='staging_server',
                testing={'platform': 'linux'},
            ),
        'UBSanVptr Linux':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                # Not a ToT bot so no clang_tot gclient_apply_config.
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER_TESTER,
                test_results_config='staging_server',
                testing={
                    'platform': 'linux',
                },
            ),
        'linux-win_cross-rel':
            bot_spec.BotSpec.create(
                chromium_config='chromium_win_clang_tot',
                chromium_apply_config=['mb', 'mb_luci_auth'],
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
                bot_type=bot_spec.BUILDER_TESTER,
                test_results_config='staging_server',
                testing={
                    'platform': 'win',
                },
                # Workaround so that recipes doesn't add random build targets to
                # our compile line. We want to build everything.
                add_tests_as_compile_targets=False,
            ),
        'ToTiOS':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                    'mac_toolchain',
                ],
                chromium_tests_apply_config=[],
                gclient_config='ios',
                gclient_apply_config=['clang_tot'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'ios',
                },
                testing={
                    'platform': 'mac',
                },
            ),
        'ToTiOSDevice':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                    'mac_toolchain',
                ],
                chromium_tests_apply_config=[],
                gclient_config='ios',
                gclient_apply_config=['clang_tot'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'ios',
                },
                testing={
                    'platform': 'mac',
                },
            ),
        'ToTWinCFI':
            bot_spec.BotSpec.create(
                chromium_config='chromium_win_clang_tot',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['clang_tot'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                compile_targets=[
                    'all',
                ],
                bot_type=bot_spec.BUILDER_TESTER,
                test_results_config='staging_server',
                testing={
                    'platform': 'win',
                },
                tests=[],
                # Workaround so that recipes doesn't add random build targets to
                # our compile line. We want to build everything.
                add_tests_as_compile_targets=False,
            ),
        'ToTWinCFI64':
            bot_spec.BotSpec.create(
                chromium_config='chromium_win_clang_tot',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['clang_tot'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                compile_targets=[
                    'all',
                ],
                bot_type=bot_spec.BUILDER_TESTER,
                test_results_config='staging_server',
                testing={
                    'platform': 'win',
                },
                tests=[],
                # Workaround so that recipes doesn't add random build targets to
                # our compile line. We want to build everything.
                add_tests_as_compile_targets=False,
            ),
        'ToTWinOfficial':
            bot_spec.BotSpec.create(
                chromium_config='chromium_win_clang_tot',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['clang_tot', 'chrome_internal'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                compile_targets=[
                    'all',
                ],
                bot_type=bot_spec.BUILDER_TESTER,
                test_results_config='staging_server',
                testing={
                    'platform': 'win',
                },
                tests=[steps.SizesStep(RESULTS_URL, 'ToTWinOfficial')],
                swarming_server='https://chrome-swarming.appspot.com',
                isolate_server='https://chrome-isolated.appspot.com',
                swarming_dimensions={
                    'pool': 'chrome.tests',
                    'os': 'Windows-10',
                },
                # Workaround so that recipes doesn't add random build targets to
                # our compile line. We want to build everything.
                add_tests_as_compile_targets=False,
            ),
        'ToTWinThinLTO64':
            bot_spec.BotSpec.create(
                chromium_config='chromium_win_clang_tot',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['clang_tot', 'chrome_internal'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                compile_targets=[
                    'all',
                ],
                bot_type=bot_spec.BUILDER_TESTER,
                test_results_config='staging_server',
                testing={
                    'platform': 'win',
                },
                tests=[steps.SizesStep(RESULTS_URL, 'ToTWinThinLTO64')],
                swarming_server='https://chrome-swarming.appspot.com',
                isolate_server='https://chrome-isolated.appspot.com',
                swarming_dimensions={
                    'pool': 'chrome.tests',
                    'os': 'Windows-10',
                },
                # Workaround so that recipes doesn't add random build targets to
                # our compile line. We want to build everything.
                add_tests_as_compile_targets=False,
            ),
        'CrWinAsan':
            bot_spec.BotSpec.create(
                chromium_config='chromium_win_clang_asan_tot',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['clang_tot'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                bot_type=bot_spec.BUILDER_TESTER,
                test_results_config='staging_server',
                testing={
                    'platform': 'win',
                },
                compile_targets=['chromium_builder_asan'],
                # add_tests_as_compile_targets not needed for the asan bot, it
                # doesn't build everything.
            ),
        'CrWinAsan(dll)':
            bot_spec.BotSpec.create(
                chromium_config='chromium_win_clang_asan_tot',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['clang_tot'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                bot_type=bot_spec.BUILDER_TESTER,
                test_results_config='staging_server',
                testing={
                    'platform': 'win',
                },
                compile_targets=['chromium_builder_asan'],
                # add_tests_as_compile_targets not needed for the asan bot, it
                # doesn't build everything.
            ),
        'ToTAndroidASan':
            bot_spec.BotSpec.create(
                chromium_config='clang_tot_android_asan',
                chromium_apply_config=['mb', 'mb_luci_auth'],
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
                bot_type=bot_spec.BUILDER_TESTER,
                android_config='clang_asan_tot_release_builder',
                test_results_config='staging_server',
                testing={
                    'platform': 'linux',
                },
                # Workaround so that recipes doesn't add random build targets to
                # our compile line. We want to build everything.
                add_tests_as_compile_targets=False,
            ),
        'ToTAndroid (dbg)':
            bot_spec.BotSpec.create(
                chromium_config='clang_tot_android_dbg',
                chromium_apply_config=['mb', 'mb_luci_auth'],
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
                bot_type=bot_spec.BUILDER_TESTER,
                android_config='clang_tot_debug_builder',
                test_results_config='staging_server',
                testing={
                    'platform': 'linux',
                },
                # Workaround so that recipes doesn't add random build targets to
                # our compile line. We want to build everything.
                add_tests_as_compile_targets=False,
            ),
        'ToTAndroid x64':
            bot_spec.BotSpec.create(
                chromium_config='clang_tot_android',
                gclient_config='chromium',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_apply_config=['clang_tot', 'android'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'android',
                },
                compile_targets=[
                    'all',
                ],
                bot_type=bot_spec.BUILDER_TESTER,
                android_config='clang_builder_mb_x64',
                test_results_config='staging_server',
                testing={
                    'platform': 'linux',
                },
                # Workaround so that recipes doesn't add random build targets to
                # our compile line. We want to build everything.
                add_tests_as_compile_targets=False,
            ),
        'ToTMac':
            bot_spec.BotSpec.create(
                chromium_config='clang_tot_mac',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['clang_tot'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                compile_targets=[
                    'all',
                ],
                bot_type=bot_spec.BUILDER_TESTER,
                test_results_config='staging_server',
                testing={
                    'platform': 'mac',
                },
                tests={steps.SizesStep(RESULTS_URL, 'ToTMac')},
                # Workaround so that recipes doesn't add random build targets to
                # our compile line. We want to build everything.
                add_tests_as_compile_targets=False,
            ),
        'ToTMacOfficial':
            bot_spec.BotSpec.create(
                chromium_config='clang_tot_mac',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['clang_tot', 'chrome_internal'],
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
                bot_type=bot_spec.BUILDER_TESTER,
                test_results_config='staging_server',
                testing={
                    'platform': 'mac',
                },
                tests={steps.SizesStep(RESULTS_URL, 'ToTMacOfficial')},
                # Workaround so that recipes doesn't add random build targets to
                # our compile line. We want to build everything.
                add_tests_as_compile_targets=False,
            ),
        'ToTMac (dbg)':
            bot_spec.BotSpec.create(
                chromium_config='clang_tot_mac',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['clang_tot'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                compile_targets=[
                    'all',
                ],
                bot_type=bot_spec.BUILDER_TESTER,
                test_results_config='staging_server',
                testing={
                    'platform': 'mac',
                },
                tests={steps.SizesStep(RESULTS_URL, 'ToTMac (dbg)')},
                # Workaround so that recipes doesn't add random build targets to
                # our compile line. We want to build everything.
                add_tests_as_compile_targets=False,
            ),
        'ToTMacASan':
            bot_spec.BotSpec.create(
                chromium_config='clang_tot_mac_asan',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['clang_tot'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                compile_targets=[
                    'all',
                ],
                bot_type=bot_spec.BUILDER_TESTER,
                test_results_config='staging_server',
                testing={
                    'platform': 'mac',
                },
                tests=[],
                # Workaround so that recipes doesn't add random build targets to
                # our compile line. We want to build everything.
                add_tests_as_compile_targets=False,
            ),
        'ToTWin':
            bot_spec.BotSpec.create(
                chromium_config='chromium_win_clang_official_tot',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['clang_tot', 'chrome_internal'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                compile_targets=[
                    'all',
                ],
                bot_type=bot_spec.BUILDER_TESTER,
                test_results_config='staging_server',
                testing={
                    'platform': 'win',
                },
                tests=[
                    steps.SizesStep(RESULTS_URL, 'ToTWin'),
                ],
                swarming_server='https://chrome-swarming.appspot.com',
                isolate_server='https://chrome-isolated.appspot.com',
                swarming_dimensions={
                    'pool': 'chrome.tests',
                    'os': 'Windows-10',
                },
                # Workaround so that recipes doesn't add random build targets to
                # our compile line. We want to build everything.
                add_tests_as_compile_targets=False,
            ),
        'ToTWin(dbg)':
            bot_spec.BotSpec.create(
                chromium_config='chromium_win_clang_tot',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['clang_tot'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 32,
                },
                compile_targets=[
                    'all',
                ],
                bot_type=bot_spec.BUILDER_TESTER,
                test_results_config='staging_server',
                testing={
                    'platform': 'win',
                },
                tests=[
                    steps.SizesStep(RESULTS_URL, 'ToTWin(dbg)'),
                ],
                # Workaround so that recipes doesn't add random build targets to
                # our compile line. We want to build everything.
                add_tests_as_compile_targets=False,
            ),
        'ToTWin(dll)':
            bot_spec.BotSpec.create(
                chromium_config='chromium_win_clang_tot',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['clang_tot'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                compile_targets=[
                    'all',
                ],
                bot_type=bot_spec.BUILDER_TESTER,
                test_results_config='staging_server',
                testing={
                    'platform': 'win',
                },
                tests=[
                    steps.SizesStep(RESULTS_URL, 'ToTWin(dll)'),
                ],
                # Workaround so that recipes doesn't add random build targets to
                # our compile line. We want to build everything.
                add_tests_as_compile_targets=False,
            ),
        'ToTWin64':
            bot_spec.BotSpec.create(
                chromium_config='chromium_win_clang_official_tot',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['clang_tot', 'chrome_internal'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                compile_targets=[
                    'all',
                ],
                bot_type=bot_spec.BUILDER_TESTER,
                test_results_config='staging_server',
                testing={
                    'platform': 'win',
                },
                tests=[
                    steps.SizesStep(RESULTS_URL, 'ToTWin64'),
                ],
                swarming_server='https://chrome-swarming.appspot.com',
                isolate_server='https://chrome-isolated.appspot.com',
                swarming_dimensions={
                    'pool': 'chrome.tests',
                    'os': 'Windows-10',
                },
                # Workaround so that recipes doesn't add random build targets to
                # our compile line. We want to build everything.
                add_tests_as_compile_targets=False,
            ),
        'ToTWinASanLibfuzzer':
            bot_spec.BotSpec.create(
                chromium_config='chromium_win_clang_asan_tot',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['clang_tot'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                compile_targets=[
                    'all',
                ],
                bot_type=bot_spec.BUILDER,
                test_results_config='staging_server',
                testing={
                    'platform': 'win',
                },
                # Workaround so that recipes doesn't add random build targets to
                # our compile line. We want to build everything.
                add_tests_as_compile_targets=False,
            ),
        'ToTWin64(dbg)':
            bot_spec.BotSpec.create(
                chromium_config='chromium_win_clang_tot',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['clang_tot'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                compile_targets=[
                    'all',
                ],
                bot_type=bot_spec.BUILDER_TESTER,
                test_results_config='staging_server',
                testing={
                    'platform': 'win',
                },
                tests=[
                    steps.SizesStep(RESULTS_URL, 'ToTWin64(dbg)'),
                ],
                # Workaround so that recipes doesn't add random build targets to
                # our compile line. We want to build everything.
                add_tests_as_compile_targets=False,
            ),
        'ToTWin64(dll)':
            bot_spec.BotSpec.create(
                chromium_config='chromium_win_clang_tot',
                chromium_apply_config=['mb', 'mb_luci_auth'],
                gclient_config='chromium',
                gclient_apply_config=['clang_tot'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                compile_targets=[
                    'all',
                ],
                bot_type=bot_spec.BUILDER_TESTER,
                test_results_config='staging_server',
                testing={
                    'platform': 'win',
                },
                tests=[
                    steps.SizesStep(RESULTS_URL, 'ToTWin64(dll)'),
                ],
                # Workaround so that recipes doesn't add random build targets to
                # our compile line. We want to build everything.
                add_tests_as_compile_targets=False,
            ),
    },
}

SPEC['builders'].update([
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
