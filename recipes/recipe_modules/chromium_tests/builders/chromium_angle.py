# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_spec


def _chromium_angle_spec(**kwargs):
  kwargs.setdefault('build_gs_bucket', 'chromium-angle-archive')
  kwargs.setdefault('gclient_config', 'chromium')
  kwargs.setdefault('isolate_server', 'https://isolateserver.appspot.com')
  return bot_spec.BotSpec.create(**kwargs)


def CreateAndroidBuilderConfig(target_bits):
  return _chromium_angle_spec(
      gclient_apply_config=[
          'android',
          'angle_internal',
          'angle_top_of_tree',
      ],
      chromium_config='android',
      android_config='main_builder_mb',
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': target_bits,
      },
      simulation_platform='linux',
  )


def CreateAndroidPerfBuilderConfig(target_bits):
  return _chromium_angle_spec(
      gclient_apply_config=[
          'android',
          'angle_internal',
          'angle_top_of_tree',
      ],
      chromium_config='android',
      android_config='main_builder_mb',
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': target_bits,
      },
      simulation_platform='linux',
      perf_isolate_upload=True,
  )


def CreateAndroidTesterConfig(target_bits, parent_builder):
  return _chromium_angle_spec(
      gclient_apply_config=[
          'android',
          'angle_internal',
          'angle_top_of_tree',
      ],
      chromium_config='android',
      android_config='main_builder_mb',
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': target_bits,
      },
      simulation_platform='linux',
      execution_mode=bot_spec.TEST,
      parent_buildername=parent_builder,
      serialize_tests=True,
  )


def CreateFuchsiaBuilderConfig(target_bits):
  return _chromium_angle_spec(
      gclient_apply_config=[
          'angle_internal',
          'angle_top_of_tree',
          'fuchsia',
      ],
      chromium_config='chromium',
      chromium_apply_config=[
          'mb',
      ],
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': target_bits,
      },
      simulation_platform='linux',
  )


def CreateBuilderConfig(platform, target_bits):
  return _chromium_angle_spec(
      gclient_apply_config=[
          'angle_internal',
          'angle_top_of_tree',
      ],
      chromium_config='chromium',
      chromium_apply_config=[
          'mb',
      ],
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': target_bits,
      },
      simulation_platform=platform,
  )


def CreateTesterConfig(platform, target_bits, parent_builder):
  return _chromium_angle_spec(
      gclient_apply_config=[
          'angle_internal',
          'angle_top_of_tree',
      ],
      chromium_config='chromium',
      chromium_apply_config=[
          'mb',
      ],
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': target_bits,
      },
      simulation_platform=platform,
      execution_mode=bot_spec.TEST,
      parent_buildername=parent_builder,
      serialize_tests=True,
  )


SPEC = {
    'android-angle-arm64-builder':
        CreateAndroidBuilderConfig(64),
    'android-angle-arm64-nexus5x':
        CreateAndroidTesterConfig(64, 'android-angle-arm64-builder'),
    'android-angle-chromium-arm64-builder':
        CreateAndroidBuilderConfig(64),
    'android-angle-chromium-arm64-nexus5x':
        CreateAndroidTesterConfig(64, 'android-angle-chromium-arm64-builder'),
    'android-angle-perf-arm64-builder':
        CreateAndroidPerfBuilderConfig(64),
    'android-angle-perf-arm64-pixel2':
        CreateAndroidTesterConfig(64, 'android-angle-perf-arm64-builder'),
    'android-angle-vk-arm-builder':
        CreateAndroidBuilderConfig(32),
    'android-angle-vk-arm-pixel2':
        CreateAndroidTesterConfig(32, 'android-angle-vk-arm-builder'),
    'android-angle-vk-arm64-builder':
        CreateAndroidBuilderConfig(64),
    'android-angle-vk-arm64-pixel2':
        CreateAndroidTesterConfig(64, 'android-angle-vk-arm64-builder'),
    'fuchsia-angle-builder':
        CreateFuchsiaBuilderConfig(64),
    'linux-angle-builder':
        CreateBuilderConfig('linux', 64),
    'linux-angle-intel':
        CreateTesterConfig('linux', 64, 'linux-angle-builder'),
    'linux-angle-nvidia':
        CreateTesterConfig('linux', 64, 'linux-angle-builder'),
    'linux-angle-chromium-builder':
        CreateBuilderConfig('linux', 64),
    'linux-angle-chromium-intel':
        CreateTesterConfig('linux', 64, 'linux-angle-chromium-builder'),
    'linux-angle-chromium-nvidia':
        CreateTesterConfig('linux', 64, 'linux-angle-chromium-builder'),
    'linux-ozone-angle-builder':
        CreateBuilderConfig('linux', 64),
    'linux-ozone-angle-intel':
        CreateTesterConfig('linux', 64, 'linux-ozone-angle-builder'),
    'mac-angle-builder':
        CreateBuilderConfig('mac', 64),
    'mac-angle-amd':
        CreateTesterConfig('mac', 64, 'mac-angle-builder'),
    'mac-angle-intel':
        CreateTesterConfig('mac', 64, 'mac-angle-builder'),
    'mac-angle-nvidia':
        CreateTesterConfig('mac', 64, 'mac-angle-builder'),
    'mac-angle-chromium-builder':
        CreateBuilderConfig('mac', 64),
    'mac-angle-chromium-amd':
        CreateTesterConfig('mac', 64, 'mac-angle-chromium-builder'),
    'mac-angle-chromium-intel':
        CreateTesterConfig('mac', 64, 'mac-angle-chromium-builder'),
    'win-angle-chromium-x64-builder':
        CreateBuilderConfig('win', 64),
    'win10-angle-chromium-x64-intel':
        CreateTesterConfig('win', 64, 'win-angle-chromium-x64-builder'),
    'win10-angle-chromium-x64-nvidia':
        CreateTesterConfig('win', 64, 'win-angle-chromium-x64-builder'),
    'win-angle-chromium-x86-builder':
        CreateBuilderConfig('win', 32),
    'win7-angle-chromium-x86-amd':
        CreateTesterConfig('win', 32, 'win-angle-chromium-x86-builder'),
    'win-angle-x64-builder':
        CreateBuilderConfig('win', 64),
    'win7-angle-x64-nvidia':
        CreateTesterConfig('win', 64, 'win-angle-x64-builder'),
    'win10-angle-x64-intel':
        CreateTesterConfig('win', 64, 'win-angle-x64-builder'),
    'win10-angle-x64-nvidia':
        CreateTesterConfig('win', 64, 'win-angle-x64-builder'),
    'win-angle-x86-builder':
        CreateBuilderConfig('win', 32),
    'win7-angle-x86-amd':
        CreateTesterConfig('win', 32, 'win-angle-x86-builder'),
}
