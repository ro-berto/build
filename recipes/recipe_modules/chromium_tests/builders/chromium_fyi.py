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
      'chromium_tests_apply_config': [],
      'isolate_server': 'https://isolateserver.appspot.com',
      'chromium_config_kwargs': {
          'BUILD_CONFIG': config,
          'TARGET_BITS': target_bits,
      },
      'chromium_tests_apply_config': [],
      'simulation_platform': platform,
      'chromium_tests_apply_config': ['use_swarming_recipe_to_trigger'],
  }
  bot_config.update(**kwargs)
  if staging:
    bot_config['chromium_tests_apply_config'].append('staging')
    bot_config['test_results_config'] = 'staging_server'
  return name, bot_spec.BotSpec.create(**bot_config)


def chromium_apply_configs(base_config, config_names):
  """chromium_apply_configs returns new config from base config with config.

  It adds config names in chromium_apply_config.

  Args:
    base_config: config obj in SPEC[x].
    config_names: a list of config names to be added into chromium_apply_config.
  Returns:
    new config obj.
  """
  return base_config.extend(
      chromium_apply_config=config_names,
      chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
  )


def no_archive(base_config):
  """no_archive returns new config from base config without archive_build etc.

  Args:
    base_config: config obj in SPEC[x].
  Returns:
    new config obj.
  """
  return base_config.evolve(
      archive_build=None, gs_bucket=None, gs_acl=None, gs_build_name=None)


SPEC = {
    'Mac Builder Next':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['use_xcode_12_beta'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='mac',
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
        ),
    'Mac11.0 Tests':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            execution_mode=bot_spec.TEST,
            parent_buildername='Mac Builder Next',
            simulation_platform='mac',
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
        ),
    'mac-osxbeta-rel':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            gclient_config='chromium',
            chromium_apply_config=['mb'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
        ),
    'fuchsia-fyi-x64-rel':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
        ),
    'Mac OpenSSL':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            test_results_config='staging_server',
            simulation_platform='mac',
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
        ),
    'Win Builder Localoutputcache':
        chromium_apply_configs(
            no_archive(chromium_win.SPEC['Win Builder']),
            ['goma_localoutputcache']),
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
        ),
    'Linux remote_run Builder':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            test_results_config='staging_server',
            simulation_platform='linux',
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
        ),
    'Linux remote_run Tester':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            execution_mode=bot_spec.TEST,
            parent_buildername='Linux remote_run Builder',
            test_specs=[
                bot_spec.TestSpec.create(steps.LocalGTestTest,
                                         'base_unittests'),
            ],
            test_results_config='staging_server',
            simulation_platform='linux',
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
        ),
    'chromeos-amd64-generic-lacros-rel':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['chromeos'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 64,
                'TARGET_CROS_BOARD': 'amd64-generic',
                'TARGET_PLATFORM': 'chromeos',
            },
            simulation_platform='linux',
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
        ),
    'ios-simulator-cr-recipe':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mac_toolchain',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='ios',  # add 'ios' to target_os
            gclient_apply_config=[],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'ios',
            },
            simulation_platform='mac',
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
        ),
    'Win10 Tests x64 1803':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            execution_mode=bot_spec.TEST,
            parent_builder_group='chromium.win',
            parent_buildername='Win x64 Builder',
            simulation_platform='win',
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
        ),
    'Win10 Tests x64 1909':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            execution_mode=bot_spec.TEST,
            parent_builder_group='chromium.win',
            parent_buildername='Win x64 Builder',
            simulation_platform='win',
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
            chromium_tests_apply_config=['use_swarming_recipe_to_trigger'],
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
    stock_config('Linux Viz'),
    stock_config('linux-annotator-rel'),
    stock_config(
        'linux-ash-chromium-builder-fyi-rel',
        gclient_apply_config=['chromeos']),
    stock_config('linux-blink-animation-use-time-delta', config='Debug'),
    stock_config('linux-blink-heap-concurrent-marking-tsan-rel'),
    stock_config('linux-blink-heap-verification'),
    stock_config('linux-chromium-tests-staging-builder'),
    stock_config(
        'linux-chromium-tests-staging-tests',
        execution_mode=bot_spec.TEST,
        parent_buildername='linux-chromium-tests-staging-builder'),
    stock_config('linux-fieldtrial-rel'),
    stock_config('linux-gcc-rel'),
    stock_config('linux-inverse-fieldtrials-fyi-rel'),
    stock_config(
        'linux-lacros-builder-fyi-rel',
        gclient_apply_config=['checkout_prebuilt_ash_chrome']),
    stock_config(
        'linux-lacros-tester-fyi-rel',
        execution_mode=bot_spec.TEST,
        parent_buildername='linux-lacros-builder-fyi-rel'),
    stock_config('linux-perfetto-rel'),
    stock_config('linux-tcmalloc-rel'),
    stock_config('linux-wpt-fyi-rel'),
    stock_config('linux-wpt-identity-fyi-rel'),
    stock_config('linux-wpt-payments-fyi-rel'),
    # For testing impact of builderful: https://crbug.com/1123673
    # remove by 2020-10-05 gatong
    stock_config('linux-builderful-fast-fyi-rel'),
    stock_config('linux-builderful-slow-fyi-rel'),
    stock_config('linux-builderless-fast-fyi-rel'),
    stock_config('linux-builderless-slow-fyi-rel'),
    stock_config('mac-hermetic-upgrade-rel'),
    stock_config('win-annotator-rel'),
    stock_config('win-pixel-builder-rel'),
    stock_config(
        'win-pixel-tester-rel',
        execution_mode=bot_spec.TEST,
        parent_buildername='win-pixel-builder-rel'),
    stock_config('win-omaha-builder-rel', staging=False),
    stock_config(
        'win7-omaha-tester-rel',
        staging=False,
        execution_mode=bot_spec.TEST,
        parent_buildername='win-omaha-builder-rel'),
    stock_config(
        'win10-omaha-tester-rel',
        staging=False,
        execution_mode=bot_spec.TEST,
        parent_buildername='win-omaha-builder-rel'),
    stock_config('mac-omaha-builder-rel', staging=False),
    stock_config(
        'mac10.10-omaha-tester-rel',
        staging=False,
        execution_mode=bot_spec.TEST,
        parent_buildername='mac-omaha-builder-rel'),
    stock_config(
        'mac10.11-omaha-tester-rel',
        staging=False,
        execution_mode=bot_spec.TEST,
        parent_buildername='mac-omaha-builder-rel'),
    stock_config(
        'mac10.12-omaha-tester-rel',
        staging=False,
        execution_mode=bot_spec.TEST,
        parent_buildername='mac-omaha-builder-rel'),
    stock_config(
        'mac10.13-omaha-tester-rel',
        staging=False,
        execution_mode=bot_spec.TEST,
        parent_buildername='mac-omaha-builder-rel'),
    stock_config(
        'mac10.14-omaha-tester-rel',
        staging=False,
        execution_mode=bot_spec.TEST,
        parent_buildername='mac-omaha-builder-rel'),
    stock_config(
        'mac10.15-omaha-tester-rel',
        staging=False,
        execution_mode=bot_spec.TEST,
        parent_buildername='mac-omaha-builder-rel'),
])

# Many of the FYI specs are made by transforming specs from other files, so
# rather than have to do 2 different things for specs based on other specs and
# specs created within this file, just evolve all of the specs afterwards
for name, spec in SPEC.iteritems():
  SPEC[name] = spec.evolve(build_gs_bucket='chromium-fyi-archive')
