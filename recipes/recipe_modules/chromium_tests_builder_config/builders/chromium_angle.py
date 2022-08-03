# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec


def _chromium_angle_spec(**kwargs):
  kwargs.setdefault('build_gs_bucket', 'chromium-angle-archive')
  kwargs.setdefault('gclient_config', 'chromium')
  return builder_spec.BuilderSpec.create(**kwargs)


def CreateAndroidBuilderConfig(target_bits):
  gclient_apply_config = [
      'android',
      'angle_top_of_tree',
      'enable_reclient',
  ]
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


def CreateAndroidTesterConfig(target_bits, parent_builder):
  gclient_apply_config = [
      'android',
      'angle_top_of_tree',
  ]
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


def CreateBuilderConfig(platform, target_bits):
  gclient_apply_config = [
      'angle_top_of_tree',
  ]
  if platform == 'linux':
    gclient_apply_config += ['enable_reclient']
  return _chromium_angle_spec(
      gclient_apply_config=gclient_apply_config,
      chromium_config='chromium',
      chromium_apply_config=[
          'mb',
      ],
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': target_bits,
          'TARGET_PLATFORM': platform,
      },
      simulation_platform=platform,
  )


def CreateTesterConfig(platform, target_bits, parent_builder):
  gclient_apply_config = [
      'angle_top_of_tree',
  ]
  return _chromium_angle_spec(
      gclient_apply_config=gclient_apply_config,
      chromium_config='chromium',
      chromium_apply_config=[
          'mb',
      ],
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': target_bits,
          'TARGET_PLATFORM': platform,
      },
      # The testers are running on linux thin bots regardless the platform.
      simulation_platform='linux',
      execution_mode=builder_spec.TEST,
      parent_buildername=parent_builder,
      serialize_tests=True,
  )


# The config for the following builders is now specified src-side in
# //infra/config/subprojects/chromium/ci/chromium.angle.star
# * ios-angle-builder
# * ios-angle-intel
SPEC = {
    'android-angle-chromium-arm64-builder':
        CreateAndroidBuilderConfig(64),
    'android-angle-chromium-arm64-nexus5x':
        CreateAndroidTesterConfig(64, 'android-angle-chromium-arm64-builder'),
    'fuchsia-angle-builder':
        CreateFuchsiaBuilderConfig(64),
    'linux-angle-chromium-builder':
        CreateBuilderConfig('linux', 64),
    'linux-angle-chromium-intel':
        CreateTesterConfig('linux', 64, 'linux-angle-chromium-builder'),
    'linux-angle-chromium-nvidia':
        CreateTesterConfig('linux', 64, 'linux-angle-chromium-builder'),
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
}
