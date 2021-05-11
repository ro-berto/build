# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.build.chromium_tests_builder_config import (builder_db,
                                                                builder_spec)


def _angle_spec(**kwargs):
  kwargs.setdefault('isolate_server', 'https://isolateserver.appspot.com')
  kwargs.setdefault('chromium_config', 'angle_clang')
  return builder_spec.BuilderSpec.create(**kwargs)


def _create_builder_config(platform, target_bits):
  return _angle_spec(
      gclient_config='angle',
      simulation_platform=platform,
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': target_bits,
      },
  )


def _create_tester_config(platform, target_bits, parent_builder):
  return _angle_spec(
      gclient_config='angle',
      simulation_platform=platform,
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': target_bits,
      },
      execution_mode=builder_spec.TEST,
      parent_buildername=parent_builder,
  )


def _create_android_builder_config(target_bits):
  return _angle_spec(
      gclient_config='angle_android',
      simulation_platform='linux',
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': target_bits,
          'TARGET_PLATFORM': 'android',
      },
  )


def _create_android_tester_config(target_bits, parent_builder):
  return _angle_spec(
      gclient_config='angle_android',
      simulation_platform='linux',
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': target_bits,
          'TARGET_PLATFORM': 'android',
      },
      execution_mode=builder_spec.TEST,
      parent_buildername=parent_builder,
  )


_SPEC = {
    'android-arm-builder':
        _create_android_builder_config(32),
    'android-arm64-builder':
        _create_android_builder_config(64),
    'android-arm64-pixel4':
        _create_android_tester_config(64, 'android-arm64-builder'),
    'linux-builder':
        _create_builder_config('linux', 64),
    'linux-intel':
        _create_tester_config('linux', 64, 'linux-builder'),
    'linux-nvidia':
        _create_tester_config('linux', 64, 'linux-builder'),
    'mac-amd':
        _create_tester_config('mac', 64, 'mac-builder'),
    'mac-builder':
        _create_builder_config('mac', 64),
    'mac-intel':
        _create_tester_config('mac', 64, 'mac-builder'),
    'mac-nvidia':
        _create_tester_config('mac', 64, 'mac-builder'),
    'win-x64-builder':
        _create_builder_config('win', 64),
    'win-x86-builder':
        _create_builder_config('win', 32),
    'win7-x86-amd':
        _create_tester_config('win', 32, 'win-x86-builder'),
    'win10-x64-intel':
        _create_tester_config('win', 64, 'win-x64-builder'),
    'win10-x64-nvidia':
        _create_tester_config('win', 64, 'win-x64-builder'),
}

BUILDERS = builder_db.BuilderDatabase.create({
    'angle': _SPEC,
})
