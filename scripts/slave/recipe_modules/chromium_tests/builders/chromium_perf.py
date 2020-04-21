# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections

from .. import bot_spec, steps

from RECIPE_MODULES.build.chromium import CONFIG_CTX as CHROMIUM_CONFIG_CTX
from RECIPE_MODULES.depot_tools.gclient import CONFIG_CTX as GCLIENT_CONFIG_CTX

SPEC = {}


@CHROMIUM_CONFIG_CTX(
    includes=['chromium', 'official', 'mb', 'goma_hermetic_fallback'])
def chromium_perf(c):
  # Bisects may build using old toolchains, so goma_hermetic_fallback is
  # required. See https://codereview.chromium.org/1015633002
  c.clobber_before_runhooks = False

  # HACK(shinyak): In perf builder, goma often fails with 'reached max
  # number of active fail fallbacks'. In fail fast mode, we cannot make the
  # number infinite currently.
  #
  # After the goma side fix, this env should be removed.
  # See http://crbug.com/606987
  c.compile_py.goma_max_active_fail_fallback_tasks = 1024


def _common_kwargs(bot_type, config_name, platform, target_bits, test_specs):
  spec = {
      'bot_type':
          bot_type,
      'chromium_config':
          config_name,
      'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': target_bits,
      },
      'enable_package_transfer':
          True,
      'gclient_config':
          config_name,
      'gclient_apply_config': [],
      'simulation_platform':
          'linux' if platform in ('android', 'chromeos') else platform,
      'test_specs':
          test_specs,
  }

  if platform == 'android':
    spec['android_config'] = 'chromium_perf'
    spec['android_apply_config'] = ['use_devil_adb']
    spec['chromium_apply_config'] = ['android', 'android_internal_isolate_maps']
    spec['chromium_config_kwargs']['TARGET_ARCH'] = 'arm'
    spec['chromium_config_kwargs']['TARGET_PLATFORM'] = 'android'
    spec['gclient_apply_config'] += ['android']
  elif platform == 'chromeos':
    spec['chromium_config_kwargs']['TARGET_PLATFORM'] = 'chromeos'
  elif platform == 'mac':
    spec['chromium_apply_config'] = ['mac_toolchain']

  spec['swarming_server'] = 'https://chrome-swarming.appspot.com'
  spec['isolate_server'] = 'https://chrome-isolated.appspot.com'
  spec['luci_project'] = 'chrome'
  return spec


def BuildSpec(config_name,
              platform,
              target_bits,
              compile_targets=None,
              extra_compile_targets=None,
              bisect_archive_build=False,
              run_sizes=True,
              cros_board=None,
              target_arch=None,
              extra_gclient_apply_config=None):
  if not compile_targets:
    compile_targets = ['chromium_builder_perf']

  test_specs = []
  # TODO: Run sizes on Android.
  # TODO (crbug.com/953108): do not run test for chromeos for now
  if run_sizes and not platform in ('android', 'chromeos'):
    test_specs = [
        bot_spec.TestSpec.create(steps.SizesStep,
                                 'https://chromeperf.appspot.com', config_name)
    ]

  kwargs = _common_kwargs(
      bot_type=bot_spec.BUILDER,
      config_name=config_name,
      platform=platform,
      target_bits=target_bits,
      test_specs=test_specs,
  )

  kwargs['perf_isolate_lookup'] = True

  kwargs['compile_targets'] = compile_targets
  if extra_compile_targets:
    kwargs['compile_targets'] += extra_compile_targets

  if cros_board:
    kwargs['chromium_config_kwargs']['TARGET_CROS_BOARD'] = cros_board

  if target_arch:
    kwargs['chromium_config_kwargs']['TARGET_ARCH'] = target_arch

  if extra_gclient_apply_config:
    kwargs['gclient_apply_config'] += list(extra_gclient_apply_config)

  kwargs['bisect_archive_build'] = bisect_archive_build
  if bisect_archive_build:
    # Bucket for storing builds for manual bisect
    kwargs['bisect_gs_bucket'] = 'chrome-test-builds'
    kwargs['bisect_gs_extra'] = 'official-by-commit'

  return bot_spec.BotSpec.create(**kwargs)


def TestSpec(config_name,
             platform,
             target_bits,
             parent_buildername,
             test_specs=None,
             cros_board=None,
             target_arch=None):
  kwargs = _common_kwargs(
      bot_type=bot_spec.TESTER,
      config_name=config_name,
      platform=platform,
      target_bits=target_bits,
      test_specs=test_specs or [],
  )

  kwargs['parent_buildername'] = parent_buildername
  kwargs['gclient_apply_config'].append('no_checkout_flash')

  if cros_board:
    kwargs['chromium_config_kwargs']['TARGET_CROS_BOARD'] = cros_board

  if target_arch:
    kwargs['chromium_config_kwargs']['TARGET_ARCH'] = target_arch

  return bot_spec.BotSpec.create(**kwargs)


def _AddIsolatedTestSpec(name, platform, parent_buildername, target_bits=64):
  spec = TestSpec(
      'chromium_perf',
      platform,
      target_bits,
      parent_buildername=parent_buildername)
  SPEC[name] = spec


def _AddBuildSpec(name,
                  platform,
                  target_bits=64,
                  bisect_archive_build=False,
                  extra_compile_targets=None):

  SPEC[name] = BuildSpec(
      'chromium_perf',
      platform,
      target_bits,
      bisect_archive_build=bisect_archive_build,
      extra_compile_targets=extra_compile_targets)


# LUCI builder
_AddBuildSpec(
    'android-builder-perf',
    'android',
    target_bits=32,
    bisect_archive_build=True,
    extra_compile_targets=[
        'android_tools',
        'cc_perftests',
        'chrome_public_apk',
        'dump_syms',
        'gpu_perftests',
        'microdump_stackwalk',
        'push_apps_to_background_apk',
        'system_webview_apk',
        'system_webview_shell_apk',
    ])

# LUCI builder
_AddBuildSpec(
    'android_arm64-builder-perf',
    'android',
    target_bits=64,
    bisect_archive_build=True,
    extra_compile_targets=[
        'android_tools',
        'cc_perftests',
        'chrome_public_apk',
        'gpu_perftests',
        'push_apps_to_background_apk',
        'system_webview_apk',
        'system_webview_shell_apk',
        'telemetry_weblayer_apks',
    ])

_AddBuildSpec('win32-builder-perf', 'win', target_bits=32)
_AddBuildSpec('win64-builder-perf', 'win', bisect_archive_build=True)
_AddBuildSpec('mac-builder-perf', 'mac', bisect_archive_build=True)

_AddBuildSpec('linux-builder-perf', 'linux', bisect_archive_build=True)

# Android: Clank, Webview, WebLayer
_AddIsolatedTestSpec(
    'Android Nexus5 Perf', 'android', 'android-builder-perf', target_bits=32)

_AddIsolatedTestSpec(
    'android-go-perf', 'android', 'android-builder-perf', target_bits=32)
_AddIsolatedTestSpec(
    'android-go_webview-perf',
    'android',
    'android-builder-perf',
    target_bits=32)

_AddIsolatedTestSpec('android-pixel2-perf', 'android',
                     'android_arm64-builder-perf')
_AddIsolatedTestSpec('android-pixel2_webview-perf', 'android',
                     'android_arm64-builder-perf')
_AddIsolatedTestSpec('android-pixel2_weblayer-perf', 'android',
                     'android_arm64-builder-perf')

_AddIsolatedTestSpec('Android Nexus5X WebView Perf', 'android',
                     'android_arm64-builder-perf')

_AddIsolatedTestSpec('win-10-perf', 'win', 'win64-builder-perf')
_AddIsolatedTestSpec('win-10_laptop_low_end-perf', 'win', 'win64-builder-perf')
_AddIsolatedTestSpec('Win 7 Perf', 'win', 'win32-builder-perf', target_bits=32)
_AddIsolatedTestSpec('Win 7 Nvidia GPU Perf', 'win', 'win64-builder-perf')

_AddIsolatedTestSpec('mac-10_12_laptop_low_end-perf', 'mac', 'mac-builder-perf')
_AddIsolatedTestSpec('mac-10_13_laptop_high_end-perf', 'mac',
                     'mac-builder-perf')

_AddIsolatedTestSpec('linux-perf', 'linux', 'linux-builder-perf')
