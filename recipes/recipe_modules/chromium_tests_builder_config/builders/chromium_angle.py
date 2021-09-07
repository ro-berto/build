# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec


def _chromium_angle_spec(**kwargs):
  kwargs.setdefault('build_gs_bucket', 'chromium-angle-archive')
  kwargs.setdefault('gclient_config', 'chromium')
  return builder_spec.BuilderSpec.create(**kwargs)


def CreateAndroidBuilderConfig(target_bits, internal):
  gclient_apply_config = [
      'android',
      'angle_top_of_tree',
  ]
  if internal:
    gclient_apply_config += ['angle_internal']
  return _chromium_angle_spec(
      gclient_apply_config=gclient_apply_config,
      chromium_config='android',
      android_config='main_builder_mb',
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': target_bits,
      },
      simulation_platform='linux',
  )


def CreateAndroidTesterConfig(target_bits, parent_builder, internal):
  gclient_apply_config = [
      'android',
      'angle_top_of_tree',
  ]
  if internal:
    gclient_apply_config += ['angle_internal']
  return _chromium_angle_spec(
      gclient_apply_config=gclient_apply_config,
      chromium_config='android',
      android_config='main_builder_mb',
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': target_bits,
      },
      simulation_platform='linux',
      execution_mode=builder_spec.TEST,
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


def CreateIOSBuilderConfig():
  return _chromium_angle_spec(
      gclient_config='ios',
      gclient_apply_config=[
          'angle_internal',
          'angle_top_of_tree',
      ],
      chromium_config='chromium',
      chromium_apply_config=[
          'mb',
          'mac_toolchain',
      ],
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
          'TARGET_PLATFORM': 'ios',
          'HOST_PLATFORM': 'mac',
      },
      simulation_platform='mac',
  )


def CreateIOSTesterConfig(parent_builder):
  return _chromium_angle_spec(
      gclient_config='ios',
      gclient_apply_config=[
          'angle_internal',
          'angle_top_of_tree',
      ],
      chromium_config='chromium',
      chromium_apply_config=[
          'mb',
          'mac_toolchain',
      ],
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
          'TARGET_PLATFORM': 'ios',
          'HOST_PLATFORM': 'mac',
      },
      simulation_platform='mac',
      execution_mode=builder_spec.TEST,
      parent_buildername=parent_builder,
      serialize_tests=True,
  )


def CreateBuilderConfig(platform, target_bits, internal):
  gclient_apply_config = [
      'angle_top_of_tree',
  ]
  if internal:
    gclient_apply_config += ['angle_internal']
  return _chromium_angle_spec(
      gclient_apply_config=gclient_apply_config,
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


def CreateTesterConfig(platform, target_bits, parent_builder, internal):
  gclient_apply_config = [
      'angle_top_of_tree',
  ]
  if internal:
    gclient_apply_config += ['angle_internal']
  return _chromium_angle_spec(
      gclient_apply_config=gclient_apply_config,
      chromium_config='chromium',
      chromium_apply_config=[
          'mb',
      ],
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': target_bits,
      },
      simulation_platform=platform,
      execution_mode=builder_spec.TEST,
      parent_buildername=parent_builder,
      serialize_tests=True,
  )


SPEC = {
    'android-angle-arm64-builder':
        CreateAndroidBuilderConfig(64, internal=True),
    'android-angle-arm64-nexus5x':
        CreateAndroidTesterConfig(
            64, 'android-angle-arm64-builder', internal=True),
    'android-angle-chromium-arm64-builder':
        CreateAndroidBuilderConfig(64, internal=False),
    'android-angle-chromium-arm64-nexus5x':
        CreateAndroidTesterConfig(
            64, 'android-angle-chromium-arm64-builder', internal=False),
    'fuchsia-angle-builder':
        CreateFuchsiaBuilderConfig(64),
    'ios-angle-builder':
        CreateIOSBuilderConfig(),
    'ios-angle-intel':
        CreateIOSTesterConfig('ios-angle-builder'),
    'linux-angle-builder':
        CreateBuilderConfig('linux', 64, internal=True),
    'linux-angle-intel':
        CreateTesterConfig('linux', 64, 'linux-angle-builder', internal=True),
    'linux-angle-nvidia':
        CreateTesterConfig('linux', 64, 'linux-angle-builder', internal=True),
    'linux-angle-chromium-builder':
        CreateBuilderConfig('linux', 64, internal=False),
    'linux-angle-chromium-intel':
        CreateTesterConfig(
            'linux', 64, 'linux-angle-chromium-builder', internal=False),
    'linux-angle-chromium-nvidia':
        CreateTesterConfig(
            'linux', 64, 'linux-angle-chromium-builder', internal=False),
    'mac-angle-chromium-builder':
        CreateBuilderConfig('mac', 64, internal=False),
    'mac-angle-chromium-amd':
        CreateTesterConfig(
            'mac', 64, 'mac-angle-chromium-builder', internal=False),
    'mac-angle-chromium-intel':
        CreateTesterConfig(
            'mac', 64, 'mac-angle-chromium-builder', internal=False),
    'win-angle-chromium-x64-builder':
        CreateBuilderConfig('win', 64, internal=False),
    'win10-angle-chromium-x64-intel':
        CreateTesterConfig(
            'win', 64, 'win-angle-chromium-x64-builder', internal=False),
    'win10-angle-chromium-x64-nvidia':
        CreateTesterConfig(
            'win', 64, 'win-angle-chromium-x64-builder', internal=False),
    'win-angle-chromium-x86-builder':
        CreateBuilderConfig('win', 32, internal=False),
    'win7-angle-chromium-x86-amd':
        CreateTesterConfig(
            'win', 32, 'win-angle-chromium-x86-builder', internal=False),
    'win-angle-x64-builder':
        CreateBuilderConfig('win', 64, internal=True),
    'win7-angle-x64-nvidia':
        CreateTesterConfig('win', 64, 'win-angle-x64-builder', internal=True),
    'win10-angle-x64-intel':
        CreateTesterConfig('win', 64, 'win-angle-x64-builder', internal=True),
    'win10-angle-x64-nvidia':
        CreateTesterConfig('win', 64, 'win-angle-x64-builder', internal=True),
    'win-angle-x86-builder':
        CreateBuilderConfig('win', 32, internal=True),
    'win7-angle-x86-amd':
        CreateTesterConfig('win', 32, 'win-angle-x86-builder', internal=True),
}
