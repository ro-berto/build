# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.build.chromium_tests_builder_config import (builder_db,
                                                                builder_spec)


def _angle_spec(**kwargs):
  kwargs.setdefault('chromium_config', 'angle_clang')
  return builder_spec.BuilderSpec.create(**kwargs)


def _create_builder_config(platform,
                           config,
                           target_bits,
                           is_clang=True,
                           perf_isolate_upload=False):
  return _angle_spec(
      chromium_config='angle_clang' if is_clang else 'angle_non_clang',
      gclient_config='angle',
      simulation_platform=platform,
      chromium_config_kwargs={
          'BUILD_CONFIG': config,
          'TARGET_BITS': target_bits,
      },
      perf_isolate_upload=perf_isolate_upload,
  )


def _create_tester_config(platform, target_bits, parent_builder):
  return _angle_spec(
      gclient_config='angle',
      simulation_platform=platform,
      chromium_config_kwargs={
          # All testing is in Release.
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': target_bits,
      },
      execution_mode=builder_spec.TEST,
      parent_buildername=parent_builder,
  )


def _create_android_builder_config(config,
                                   target_bits,
                                   perf_isolate_upload=False):
  return _angle_spec(
      gclient_config='angle_android',
      simulation_platform='linux',
      chromium_config_kwargs={
          'BUILD_CONFIG': config,
          'TARGET_BITS': target_bits,
          'TARGET_PLATFORM': 'android',
      },
      perf_isolate_upload=perf_isolate_upload,
  )


def _create_android_tester_config(target_bits, parent_builder):
  return _angle_spec(
      gclient_config='angle_android',
      simulation_platform='linux',
      chromium_config_kwargs={
          # All testing is in Release.
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': target_bits,
          'TARGET_PLATFORM': 'android',
      },
      execution_mode=builder_spec.TEST,
      parent_buildername=parent_builder,
  )


_SPEC = {
    'android-arm-compile':
        _create_android_builder_config('Release', 32),
    'android-arm-dbg-compile':
        _create_android_builder_config('Debug', 32),
    'android-arm64-dbg':
        _create_android_builder_config('Debug', 64),
    'android-arm64-dbg-compile':
        _create_android_builder_config('Debug', 64),
    'android-arm64-pixel4':
        _create_android_tester_config(64, 'android-arm64-test'),
    'android-arm64-pixel4-perf':
        _create_android_tester_config(64, 'android-perf'),
    'android-arm64-test':
        _create_android_builder_config('Release', 64),
    'android-perf':
        _create_android_builder_config('Release', 64, perf_isolate_upload=True),
    'linux-dbg-compile':
        _create_builder_config('linux', 'Debug', 64),
    'linux-intel':
        _create_tester_config('linux', 64, 'linux-test'),
    'linux-intel-perf':
        _create_tester_config('linux', 64, 'linux-perf'),
    'linux-nvidia':
        _create_tester_config('linux', 64, 'linux-test'),
    'linux-nvidia-perf':
        _create_tester_config('linux', 64, 'linux-perf'),
    'linux-perf':
        _create_builder_config(
            'linux', 'Release', 64, perf_isolate_upload=True),
    'linux-swiftshader':
        _create_tester_config('linux', 64, 'linux-test'),
    'linux-test':
        _create_builder_config('linux', 'Release', 64),
    'linux-trace':
        _create_builder_config('linux', 'Release', 64),
    'mac-amd':
        _create_tester_config('mac', 64, 'mac-test'),
    'mac-dbg-compile':
        _create_builder_config('mac', 'Debug', 64),
    'mac-intel':
        _create_tester_config('mac', 64, 'mac-test'),
    'mac-nvidia':
        _create_tester_config('mac', 64, 'mac-test'),
    'mac-test':
        _create_builder_config('mac', 'Release', 64),
    'win-dbg-compile':
        _create_builder_config('win', 'Debug', 64),
    'win-msvc-compile':
        _create_builder_config('win', 'Release', 64, is_clang=False),
    'win-msvc-dbg-compile':
        _create_builder_config('win', 'Debug', 64, is_clang=False),
    'win-msvc-x86-compile':
        _create_builder_config('win', 'Release', 32, is_clang=False),
    'win-msvc-x86-dbg-compile':
        _create_builder_config('win', 'Debug', 32, is_clang=False),
    'win-perf':
        _create_builder_config('win', 'Release', 64, perf_isolate_upload=True),
    'win-test':
        _create_builder_config('win', 'Release', 64),
    'win-trace':
        _create_builder_config('win', 'Release', 64),
    'win-x86-dbg-compile':
        _create_builder_config('win', 'Debug', 32),
    'win-x86-test':
        _create_builder_config('win', 'Release', 32),
    'winuwp-compile':
        _create_builder_config('win', 'Release', 64, is_clang=False),
    'winuwp-dbg-compile':
        _create_builder_config('win', 'Debug', 64, is_clang=False),
    'win7-x86-amd':
        _create_tester_config('win', 32, 'win-x86-test'),
    'win10-x64-intel':
        _create_tester_config('win', 64, 'win-test'),
    'win10-x64-intel-perf':
        _create_tester_config('win', 64, 'win-perf'),
    'win10-x64-nvidia':
        _create_tester_config('win', 64, 'win-test'),
    'win10-x64-nvidia-perf':
        _create_tester_config('win', 64, 'win-perf'),
    'win10-x86-swiftshader':
        _create_tester_config('win', 32, 'win-x86-test'),
}

BUILDERS = builder_db.BuilderDatabase.create({
    'angle': _SPEC,
})
