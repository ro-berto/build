# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections

from .. import bot_spec, steps

from RECIPE_MODULES.build.chromium import CONFIG_CTX as CHROMIUM_CONFIG_CTX
from RECIPE_MODULES.depot_tools.gclient import CONFIG_CTX as GCLIENT_CONFIG_CTX

SPEC = {}


@CHROMIUM_CONFIG_CTX(includes=[
    'chromium',
    'official',
    'mb',
    'goma_hermetic_fallback',
])
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


def _common_kwargs(execution_mode, config_name, platform, target_bits):
  spec = {
      'execution_mode':
          execution_mode,
      'chromium_config':
          config_name,
      'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': target_bits,
      },
      'gclient_config':
          config_name,
      'gclient_apply_config': [],
      'simulation_platform':
          'linux' if platform in ('android', 'chromeos',
                                  'fuchsia') else platform,
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
    spec['gclient_apply_config'] += ['chromeos']
  elif platform == 'fuchsia':
    spec['chromium_config_kwargs']['TARGET_PLATFORM'] = 'fuchsia'

  spec['swarming_server'] = 'https://chrome-swarming.appspot.com'
  spec['isolate_server'] = 'https://chrome-isolated.appspot.com'
  spec['luci_project'] = 'chrome'
  return spec


def BuildSpec(config_name,
              platform,
              target_bits,
              bisect_archive_build=False,
              cros_boards=None,
              target_arch=None,
              extra_gclient_apply_config=None):

  kwargs = _common_kwargs(
      execution_mode=bot_spec.COMPILE_AND_TEST,
      config_name=config_name,
      platform=platform,
      target_bits=target_bits,
  )

  kwargs['perf_isolate_upload'] = True

  if cros_boards:
    kwargs['chromium_config_kwargs']['TARGET_CROS_BOARDS'] = cros_boards

  if target_arch:
    kwargs['chromium_config_kwargs']['TARGET_ARCH'] = target_arch

  kwargs['gclient_apply_config'] += ['checkout_pgo_profiles']
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
             cros_boards=None,
             target_arch=None):
  kwargs = _common_kwargs(
      execution_mode=bot_spec.TEST,
      config_name=config_name,
      platform=platform,
      target_bits=target_bits,
  )

  kwargs['parent_buildername'] = parent_buildername
  kwargs['gclient_apply_config'].append('chromium_skip_wpr_archives_download')

  if cros_boards:
    kwargs['chromium_config_kwargs']['TARGET_CROS_BOARDS'] = cros_boards

  if target_arch:
    kwargs['chromium_config_kwargs']['TARGET_ARCH'] = target_arch

  return bot_spec.BotSpec.create(**kwargs)


def _AddIsolatedTestSpec(name,
                         platform,
                         parent_buildername,
                         target_bits=64,
                         target_arch=None,
                         cros_boards=None):
  spec = TestSpec(
      'chromium_perf',
      platform,
      target_bits,
      parent_buildername=parent_buildername,
      cros_boards=cros_boards,
      target_arch=target_arch)
  SPEC[name] = spec


def _AddBuildSpec(name,
                  platform,
                  target_bits=64,
                  bisect_archive_build=False,
                  target_arch=None,
                  gclient_apply_config=None):
  SPEC[name] = BuildSpec(
      'chromium_perf',
      platform,
      target_bits,
      bisect_archive_build=bisect_archive_build,
      target_arch=target_arch,
      extra_gclient_apply_config=gclient_apply_config)


# LUCI builder
_AddBuildSpec(
    'android-builder-perf',
    'android',
    target_bits=32,
    bisect_archive_build=True)

# LUCI builder
_AddBuildSpec(
    'android_arm64-builder-perf',
    'android',
    target_bits=64,
    bisect_archive_build=True)

_AddBuildSpec('win32-builder-perf', 'win', target_bits=32)
_AddBuildSpec('win64-builder-perf', 'win', bisect_archive_build=True)
_AddBuildSpec('mac-builder-perf', 'mac', bisect_archive_build=True)
_AddBuildSpec(
    'mac-arm-builder-perf',
    'mac',
    bisect_archive_build=True,
    target_arch='arm',
)

# Adapted from 'chromeos-amd64-generic-lacros-internal' to measure binary size.
SPEC.update({
    'chromeos-amd64-generic-lacros-builder-perf':
        bot_spec.BotSpec.create(
            chromium_config='chromium_perf',
            gclient_apply_config=['chromeos'],
            gclient_config='chromium_perf',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 64,
                'TARGET_CROS_BOARDS': 'amd64-generic:eve',
                'TARGET_PLATFORM': 'chromeos',
            },
            simulation_platform='linux',
            isolate_server='https://chrome-isolated.appspot.com',
            swarming_server='https://chrome-swarming.appspot.com',
            bisect_archive_build=True,
            bisect_gs_bucket='chrome-test-builds',
            bisect_gs_extra='official-by-commit',
        ),
})

_AddBuildSpec('linux-builder-perf', 'linux', bisect_archive_build=True)
_AddBuildSpec('linux-builder-perf-rel', 'linux')

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

_AddIsolatedTestSpec('android-pixel4-perf', 'android',
                     'android_arm64-builder-perf')
_AddIsolatedTestSpec('android-pixel4_webview-perf', 'android',
                     'android_arm64-builder-perf')
_AddIsolatedTestSpec('android-pixel4_weblayer-perf', 'android',
                     'android_arm64-builder-perf')

_AddIsolatedTestSpec('android-pixel4a_power-perf', 'android',
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
_AddIsolatedTestSpec(
    'mac-m1_mini_2020-perf', 'mac', 'mac-arm-builder-perf', target_arch='arm')

_AddIsolatedTestSpec('linux-perf', 'linux', 'linux-builder-perf')
_AddIsolatedTestSpec('linux-perf-rel', 'linux', 'linux-builder-perf-rel')

_AddIsolatedTestSpec(
    'lacros-eve-perf',
    'chromeos',
    'chromeos-amd64-generic-lacros-builder-perf',
    target_bits=64,
    target_arch='intel',
    cros_boards='amd64-generic:eve')

# Perf result processors
_AddIsolatedTestSpec('linux-processor-perf', 'linux', 'linux-perf')

_AddIsolatedTestSpec(
    'android-go-processor-perf', 'android', 'android-go-perf', target_bits=32)
_AddIsolatedTestSpec('android-pixel2-processor-perf', 'android',
                     'android-pixel2-perf')
_AddIsolatedTestSpec('android-pixel2_webview-processor-perf', 'android',
                     'android-pixel2_webview-perf')

_AddIsolatedTestSpec('win-10-processor-perf', 'win', 'win-10-perf')
_AddIsolatedTestSpec('win-10_laptop_low_end-processor-perf', 'win',
                     'win-10_laptop_low_end-perf')

_AddIsolatedTestSpec('mac-10_12_laptop_low_end-processor-perf', 'mac',
                     'mac-10_12_laptop_low_end-perf')
_AddIsolatedTestSpec('mac-10_13_laptop_high_end-processor-perf', 'mac',
                     'mac-10_13_laptop_high_end-perf')
