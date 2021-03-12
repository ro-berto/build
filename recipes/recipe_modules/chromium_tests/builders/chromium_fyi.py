# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_spec, steps
from . import chromium
from . import chromium_linux
from . import chromium_mac
from . import chromium_win

RESULTS_URL = 'https://chromeperf.appspot.com'


def stock_config(name, config='Release', target_bits=64, staging=True,
                 **kwargs):
  if 'mac' in name.lower():
    platform = 'mac'
  elif 'win' in name.lower():
    platform = 'win'
  elif 'linux' in name.lower():
    platform = 'linux'
  assert (platform)

  bot_config = {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['mb',],
      'isolate_server': 'https://isolateserver.appspot.com',
      'chromium_config_kwargs': {
          'BUILD_CONFIG': config,
          'TARGET_BITS': target_bits,
      },
      'simulation_platform': platform,
  }
  bot_config.update(**kwargs)
  if staging:
    bot_config['test_results_config'] = 'staging_server'
  return name, bot_spec.BotSpec.create(**bot_config)


SPEC = {
    'Mac Builder Next':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            isolate_server='https://isolateserver.appspot.com',
            isolate_use_cas=True,
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='mac',
        ),
    'Mac11.0 Tests':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            isolate_server='https://isolateserver.appspot.com',
            isolate_use_cas=True,
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            execution_mode=bot_spec.TEST,
            parent_buildername='Mac Builder Next',
            simulation_platform='mac',
        ),
    'mac-arm64-rel-tests':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            },
            swarming_dimensions={
                'cpu': 'arm',
            },
            execution_mode=bot_spec.TEST,
            parent_builder_group='chromium.mac',
            parent_buildername='mac-arm64-rel',
            simulation_platform='mac',
        ),
    'mac-osxbeta-rel':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            gclient_config='chromium',
            chromium_apply_config=[
                'mb',
                'goma_use_local',  # to mitigate compile step timeout (crbug.com/1056935).
            ],
            isolate_server='https://isolateserver.appspot.com',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            swarming_dimensions={
                'os': 'Mac-10.14',
            },
            execution_mode=bot_spec.TEST,
            test_results_config='staging_server',
            parent_builder_group='chromium.mac',
            parent_buildername='Mac Builder',
            simulation_platform='mac',
        ),
    # There are no slaves for the following two "Dummy Builders" and they
    # do not appear on the actual continuous waterfall; this configuration
    # is here so that a try bot can be added.
    'WebKit Linux composite_after_paint Dummy Builder':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    'WebKit Linux layout_ng_disabled Builder':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    'fuchsia-fyi-arm64-dbg':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['fuchsia_arm64', 'fuchsia_arm64_host'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'fuchsia',
            },
            # Serialize the tests to limit capacity usage.
            serialize_tests=True,
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    'fuchsia-fyi-arm64-rel':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['fuchsia_arm64', 'fuchsia_arm64_host'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'fuchsia',
            },
            # Serialize the tests to limit capacity usage.
            serialize_tests=True,
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    'fuchsia-fyi-arm64-size':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['fuchsia_arm64', 'fuchsia_arm64_host'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'fuchsia',
            },
            # Serialize the tests to limit capacity usage.
            serialize_tests=True,
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    'fuchsia-fyi-x64-dbg':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['fuchsia_x64'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'fuchsia',
            },
            # Serialize the tests to limit capacity usage.
            serialize_tests=True,
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    'fuchsia-fyi-x64-rel':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            isolate_use_cas=True,
            gclient_config='chromium',
            gclient_apply_config=['fuchsia_x64'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'fuchsia',
            },
            # Serialize the tests to limit capacity usage.
            serialize_tests=True,
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    'lacros-amd64-generic-rel-fyi':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['chromeos'],
            chromium_config_kwargs={
                'TARGET_BITS': 64,
                'CROS_BOARDS_WITH_QEMU_IMAGES': 'amd64-generic',
                'TARGET_PLATFORM': 'chromeos',
            },
            simulation_platform='linux',
            test_results_config='staging_server',
        ),
    'linux-paeverywhere-x64-fyi-dbg':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_use_cas=True,
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'linux',
            },
            simulation_platform='linux',
            test_results_config='staging_server',
        ),
    'linux-paeverywhere-x64-fyi-rel':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'linux',
            },
            simulation_platform='linux',
            test_results_config='staging_server',
        ),
    'mac-paeverywhere-x64-fyi-dbg':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'mac',
            },
            simulation_platform='mac',
            test_results_config='staging_server',
        ),
    'mac-paeverywhere-x64-fyi-rel':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'mac',
            },
            simulation_platform='mac',
            test_results_config='staging_server',
        ),
    'win-paeverywhere-x64-fyi-dbg':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'win',
            },
            simulation_platform='win',
            test_results_config='staging_server',
        ),
    'win-paeverywhere-x64-fyi-rel':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_use_cas=True,
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'win',
            },
            simulation_platform='win',
            test_results_config='staging_server',
        ),
    'win-paeverywhere-x86-fyi-dbg':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'win',
            },
            simulation_platform='win',
            test_results_config='staging_server',
        ),
    'win-paeverywhere-x86-fyi-rel':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'win',
            },
            simulation_platform='win',
            test_results_config='staging_server',
        ),
    'android-paeverywhere-arm64-fyi-dbg':
        bot_spec.BotSpec.create(
            chromium_config='android',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            simulation_platform='linux',
            test_results_config='staging_server',
        ),
    'android-paeverywhere-arm64-fyi-rel':
        bot_spec.BotSpec.create(
            chromium_config='android',
            chromium_apply_config=['mb'],
            isolate_use_cas=True,
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            simulation_platform='linux',
            test_results_config='staging_server',
        ),
    'android-paeverywhere-arm-fyi-dbg':
        bot_spec.BotSpec.create(
            chromium_config='android',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            simulation_platform='linux',
            test_results_config='staging_server',
        ),
    'android-paeverywhere-arm-fyi-rel':
        bot_spec.BotSpec.create(
            chromium_config='android',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            simulation_platform='linux',
            test_results_config='staging_server',
        ),
    'Site Isolation Android':
        bot_spec.BotSpec.create(
            chromium_config='android',
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='arm64_builder_mb',
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    # For building targets instrumented for code coverage.
    'linux-code-coverage':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'goma_high_parallel',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['use_clang_coverage'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'fuchsia-code-coverage':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['fuchsia_x64', 'use_clang_coverage'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'fuchsia',
            },
            simulation_platform='linux',
        ),
    'mac-code-coverage':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['use_clang_coverage'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='mac',
        ),
    'win32-arm64-rel':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            gclient_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_ARCH': 'arm'
            },
            simulation_platform='win',
        ),
    'Win 10 Fast Ring':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            test_results_config='staging_server',
            simulation_platform='win',
        ),
    'linux-autofill-captured-sites-rel':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            gclient_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'linux',
            },
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
    'linux-chromeos-code-coverage':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'goma_high_parallel',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['chromeos', 'use_clang_coverage'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'linux-example-builder':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            execution_mode=bot_spec.COMPILE_AND_TEST,
            simulation_platform='linux',
        ),
    'linux-chromeos-js-code-coverage':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'goma_high_parallel',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['chromeos'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'ios-simulator-cronet':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='ios',
            gclient_apply_config=[],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
                'HOST_PLATFORM': 'mac',
            },
            simulation_platform='mac',
        ),
    'ios-webkit-tot':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='ios',
            gclient_apply_config=['ios_webkit_tot'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
            },
            simulation_platform='mac',
        ),
    'ios13-beta-simulator':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='ios',
            gclient_apply_config=[],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
                'HOST_PLATFORM': 'mac',
            },
            simulation_platform='mac',
        ),
    'ios13-sdk-device':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='ios',
            gclient_apply_config=[],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
            },
            simulation_platform='mac',
        ),
    'ios13-sdk-simulator':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='ios',
            gclient_apply_config=[],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
                'HOST_PLATFORM': 'mac',
            },
            simulation_platform='mac',
        ),
    'ios14-beta-simulator':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='ios',
            gclient_apply_config=[],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
                'HOST_PLATFORM': 'mac',
            },
            simulation_platform='mac',
        ),
    'ios14-sdk-simulator':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='ios',
            gclient_apply_config=[],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
                'HOST_PLATFORM': 'mac',
            },
            simulation_platform='mac',
        ),
    'ios-asan':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='ios',
            gclient_apply_config=[],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
                'HOST_PLATFORM': 'mac',
            },
            simulation_platform='mac',
        ),
    'ios-simulator-multi-window':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='ios',
            gclient_apply_config=[],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
                'HOST_PLATFORM': 'mac',
            },
            simulation_platform='mac',
        ),
    'ios-simulator-code-coverage':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='ios',
            gclient_apply_config=['use_clang_coverage'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
                'HOST_PLATFORM': 'mac',
            },
            simulation_platform='mac',
        ),
    'android-code-coverage':
        bot_spec.BotSpec.create(
            chromium_config='android',
            chromium_apply_config=['download_vr_test_apks', 'mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            simulation_platform='linux',
        ),
    'android-code-coverage-native':
        bot_spec.BotSpec.create(
            chromium_config='android',
            chromium_apply_config=['download_vr_test_apks', 'mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android', 'use_clang_coverage'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            simulation_platform='linux',
        ),
    'win10-code-coverage':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'goma_high_parallel',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['use_clang_coverage'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='win',
        ),
    'linux-upload-perfetto':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'mac-upload-perfetto':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='mac',
        ),
    'win-upload-perfetto':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='win',
        ),
    'Linux Builder (reclient)':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['use_clang_coverage', 'enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'Linux Builder (runsc-exp) (reclient)':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['use_clang_coverage', 'enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'Linux Builder (goma cache silo)':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb', 'goma_enable_cache_silo'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['use_clang_coverage'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'Linux TSan Builder (goma cache silo)':
        bot_spec.BotSpec.create(
            chromium_config='chromium_tsan2',
            chromium_apply_config=['mb', 'goma_enable_cache_silo'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
            build_gs_bucket='chromium-memory-archive',
        ),
    # Shadow of 'Linux TSan Builder' that runs on re-client
    # https://source.chromium.org/chromium/chromium/tools/build/+/master:recipes/recipe_modules/chromium_tests/builders/chromium_memory.py;l=142-153;drc=f0bea90284b4f79199b3f4e7b577e6b31d395680
    # Add it as an FYI builder, so that its failure doesn't notify anyone.
    'Linux TSan Builder (reclient)':
        bot_spec.BotSpec.create(
            chromium_config='chromium_tsan2',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
            build_gs_bucket='chromium-memory-archive',
        ),
    'TSAN Release (reclient)':
        bot_spec.BotSpec.create(
            chromium_config='chromium_clang',
            chromium_apply_config=['mb', 'tsan2', 'clobber'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            # Set archive build to false since this is a shadow.
            cf_archive_build=False,
            simulation_platform='linux',
        ),
    'TSAN Debug (reclient)':
        bot_spec.BotSpec.create(
            chromium_config='chromium_clang',
            chromium_apply_config=['mb', 'tsan2', 'clobber'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            # Set archive_build to false since this is a shadow.
            cf_archive_build=False,
            simulation_platform='linux',
        ),
    'ASAN Debug (reclient)':
        bot_spec.BotSpec.create(
            # Maybe remove the 'chromium_asan' config if this builder is
            # removed.
            chromium_config='chromium_asan',
            chromium_apply_config=['mb', 'clobber'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            cf_archive_build=False,
            simulation_platform='linux',
        ),
    'UBSan Release (reclient)':
        bot_spec.BotSpec.create(
            chromium_config='chromium_linux_ubsan',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            cf_archive_build=False,
            simulation_platform='linux',
        ),
    'Win x64 Builder (reclient)':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['use_clang_coverage', 'enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='win',
        ),
}

SPEC.update([
    stock_config('linux-blink-rel-dummy', staging=False),
    stock_config('linux-blink-optional-highdpi-rel-dummy', staging=False),
    stock_config('mac10.12-blink-rel-dummy', staging=False),
    stock_config('mac10.13-blink-rel-dummy', staging=False),
    stock_config('mac10.14-blink-rel-dummy', staging=False),
    stock_config('mac10.15-blink-rel-dummy', staging=False),
    stock_config('mac11.0-blink-rel-dummy', staging=False),
    stock_config('win7-blink-rel-dummy', target_bits=32, staging=False),
    stock_config('win10-blink-rel-dummy', target_bits=32, staging=False),
    stock_config('VR Linux'),
    stock_config(
        'VR Linux (reclient)', gclient_apply_config=['enable_reclient']),
    stock_config('Linux Viz'),
    stock_config('linux-annotator-rel'),
    stock_config(
        'linux-ash-chromium-builder-fyi-rel',
        gclient_apply_config=['chromeos']),
    stock_config('linux-blink-animation-use-time-delta', config='Debug'),
    stock_config('linux-blink-heap-concurrent-marking-tsan-rel'),
    stock_config('linux-blink-heap-verification'),
    stock_config('linux-blink-v8-oilpan'),
    stock_config('linux-chromium-tests-staging-builder'),
    stock_config(
        'linux-chromium-tests-staging-tests',
        execution_mode=bot_spec.TEST,
        parent_buildername='linux-chromium-tests-staging-builder'),
    stock_config('linux-fieldtrial-rel'),
    stock_config('linux-gcc-rel'),
    stock_config(
        'linux-lacros-builder-fyi-rel', gclient_apply_config=['chromeos']),
    stock_config(
        'linux-lacros-tester-fyi-rel',
        execution_mode=bot_spec.TEST,
        parent_buildername='linux-lacros-builder-fyi-rel'),
    stock_config('linux-perfetto-rel'),
    stock_config('linux-tcmalloc-rel'),
    stock_config('linux-wpt-fyi-rel'),
    # Despite the FYI name, these are the "MVP bots" used by teams:
    # https://source.chromium.org/chromium/chromium/src/+/master:docs/testing/web_platform_tests_wptrunner.md;l=64;drc=5ce5d37c5ebfbd3b658f1f68173be7573a95d0ea
    stock_config('linux-wpt-identity-fyi-rel', staging=False),
    stock_config('linux-wpt-input-fyi-rel', staging=False),
    stock_config('mac-hermetic-upgrade-rel'),
    stock_config('win-annotator-rel'),
    stock_config('win-pixel-builder-rel'),
    stock_config(
        'win-pixel-tester-rel',
        execution_mode=bot_spec.TEST,
        parent_buildername='win-pixel-builder-rel'),
])

# Many of the FYI specs are made by transforming specs from other files, so
# rather than have to do 2 different things for specs based on other specs and
# specs created within this file, just evolve all of the specs afterwards
for name, spec in SPEC.iteritems():
  SPEC[name] = spec.evolve(build_gs_bucket='chromium-fyi-archive')
