# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.build.chromium_tests_builder_config import (builder_db,
                                                                builder_spec)


def _angle_spec(**kwargs):
  kwargs.setdefault('gclient_config', 'angle')
  kwargs.setdefault('isolate_server', 'https://isolateserver.appspot.com')
  return builder_spec.BuilderSpec.create(**kwargs)


def _create_builder_config(platform, target_bits, internal):
  gclient_apply_config = []
  if internal:
    gclient_apply_config += ['angle_internal']
  return _angle_spec(
      gclient_apply_config=gclient_apply_config,
      chromium_config='angle',
      chromium_apply_config=[
          'mb',
      ],
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': target_bits,
      },
      simulation_platform=platform,
  )


def _create_tester_config(platform, target_bits, parent_builder, internal):
  gclient_apply_config = []
  if internal:
    gclient_apply_config += ['angle_internal']
  return _angle_spec(
      gclient_apply_config=gclient_apply_config,
      chromium_config='angle',
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
  )


_SPEC = {
    'android-arm-builder':
        _create_builder_config('linux', 32, internal=True),
    'android-arm64-builder':
        _create_builder_config('linux', 64, internal=True),
    'linux-builder':
        _create_builder_config('linux', 64, internal=True),
    'linux-intel':
        _create_tester_config('linux', 64, 'linux-builder', internal=True),
    'linux-nvidia':
        _create_tester_config('linux', 64, 'linux-builder', internal=True),
    'mac-amd':
        _create_tester_config('mac', 64, 'mac-builder', internal=True),
    'mac-builder':
        _create_builder_config('mac', 64, internal=True),
    'mac-intel':
        _create_tester_config('mac', 64, 'mac-builder', internal=True),
    'mac-nvidia':
        _create_tester_config('mac', 64, 'mac-builder', internal=True),
    'win-x64-builder':
        _create_builder_config('win', 64, internal=True),
    'win-x86-builder':
        _create_builder_config('win', 32, internal=True),
    'win7-x86-amd':
        _create_tester_config('win', 32, 'win-x86-builder', internal=True),
    'win10-x64-intel':
        _create_tester_config('win', 64, 'win-x64-builder', internal=True),
    'win10-x64-nvidia':
        _create_tester_config('win', 64, 'win-x64-builder', internal=True),
}

BUILDERS = builder_db.BuilderDatabase.create({
    'angle': _SPEC,
})
