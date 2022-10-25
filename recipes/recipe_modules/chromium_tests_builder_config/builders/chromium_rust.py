# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec


def CreateRustBuilder(platform, is_dbg):
  chromium_config = {
      'BUILD_CONFIG': 'Debug' if is_dbg else 'Release',
  }
  if platform == 'android':
    chromium_config.update({
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
        'TARGET_ARCH': 'arm',
    })
  else:  # platform == 'linux'
    chromium_config.update({
        'TARGET_BITS': 64,
    })

  return builder_spec.BuilderSpec.create(
      chromium_config='android' if platform == 'android' else 'chromium',
      chromium_apply_config=['android' if platform == 'android' else 'mb'],
      gclient_config='chromium',
      gclient_apply_config=['use_rust'] +
      (['android'] if platform == 'android' else []),
      chromium_config_kwargs=chromium_config,
      android_config='base_config' if platform == 'android' else None,
      simulation_platform='linux',
  )


SPEC = {
    'linux-rust-x64-dbg': CreateRustBuilder('linux', True),
    'linux-rust-x64-rel': CreateRustBuilder('linux', False),
    'android-rust-arm-dbg': CreateRustBuilder('android', True),
    'android-rust-arm-rel': CreateRustBuilder('android', False),
}
