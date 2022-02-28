# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec


def CreateAndroidBuilder():
  return builder_spec.BuilderSpec.create(
      chromium_config='android',
      chromium_apply_config=['android'],
      gclient_config='chromium',
      gclient_apply_config=['android', 'enable_reclient'],
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
      },
      android_config='base_config',
      simulation_platform='linux',
  )


def CreateLinuxBuilder():
  return builder_spec.BuilderSpec.create(
      chromium_config='chromium',
      chromium_apply_config=['mb'],
      gclient_config='chromium',
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
      },
      simulation_platform='linux',
  )


def CreateLinuxInTreeToolchainBuilder():
  return builder_spec.BuilderSpec.create(
      chromium_config='chromium',
      chromium_apply_config=['mb'],
      gclient_config='chromium',
      gclient_apply_config=['rust_in_tree'],
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
      },
      simulation_platform='linux',
  )


SPEC = {
    'linux-rust-x64-rel': CreateLinuxBuilder(),
    'linux-rust-intree-x64-rel': CreateLinuxInTreeToolchainBuilder(),
    'android-rust-arm-rel': CreateAndroidBuilder(),
}
