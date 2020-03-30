# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import bot_spec


def _chromium_gpu_spec(**kwargs):
  return bot_spec.BotSpec.create(
      build_gs_bucket='chromium-gpu-archive', **kwargs)


SPEC = {
    'builders': {
        'GPU Win x64 Builder':
            _chromium_gpu_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'win',
                },
            ),
        'GPU Win x64 Builder Code Coverage':
            _chromium_gpu_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                gclient_apply_config=['use_clang_coverage'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'win',
                },
            ),
        'GPU Win x64 Builder (dbg)':
            _chromium_gpu_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'win',
                },
            ),
        'Win10 x64 Release (NVIDIA)':
            _chromium_gpu_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU Win x64 Builder',
                testing={
                    'platform': 'win',
                },
            ),
        'Win10 x64 Release (NVIDIA) Code Coverage':
            _chromium_gpu_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                gclient_apply_config=['use_clang_coverage'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU Win x64 Builder Code Coverage',
                testing={
                    'platform': 'win',
                },
            ),
        'Win10 x64 Debug (NVIDIA)':
            _chromium_gpu_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU Win x64 Builder (dbg)',
                testing={
                    'platform': 'win',
                },
            ),
        'GPU Linux Builder':
            _chromium_gpu_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                    'goma_high_parallel',
                ],
                gclient_config='chromium',
                gclient_apply_config=['use_clang_coverage'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'linux',
                },
            ),
        'GPU Linux Builder (dbg)':
            _chromium_gpu_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'linux',
                },
            ),
        'Linux Release (NVIDIA)':
            _chromium_gpu_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                    'goma_high_parallel',
                ],
                gclient_config='chromium',
                gclient_apply_config=['use_clang_coverage'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU Linux Builder',
                testing={
                    'platform': 'linux',
                },
            ),
        'Linux Debug (NVIDIA)':
            _chromium_gpu_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU Linux Builder (dbg)',
                testing={
                    'platform': 'linux',
                },
            ),
        'GPU Mac Builder':
            _chromium_gpu_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'mac',
                },
            ),
        'GPU Mac Builder (dbg)':
            _chromium_gpu_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'mac',
                },
            ),
        'GPU Mac Builder Code Coverage':
            _chromium_gpu_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                gclient_apply_config=['use_clang_coverage'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'mac',
                },
            ),
        'Mac Release (Intel)':
            _chromium_gpu_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU Mac Builder',
                testing={
                    'platform': 'mac',
                },
            ),
        'Mac Release (Intel) Code Coverage':
            _chromium_gpu_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                gclient_apply_config=['use_clang_coverage'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU Mac Builder Code Coverage',
                testing={
                    'platform': 'mac',
                },
            ),
        'Mac Debug (Intel)':
            _chromium_gpu_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU Mac Builder (dbg)',
                testing={
                    'platform': 'mac',
                },
            ),
        'Mac Retina Release (AMD)':
            _chromium_gpu_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU Mac Builder',
                testing={
                    'platform': 'mac',
                },
            ),
        'Mac Retina Release (AMD) Code Coverage':
            _chromium_gpu_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                gclient_apply_config=['use_clang_coverage'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU Mac Builder Code Coverage',
                testing={
                    'platform': 'mac',
                },
            ),
        'Mac Retina Debug (AMD)':
            _chromium_gpu_spec(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU Mac Builder (dbg)',
                testing={
                    'platform': 'mac',
                },
            ),
        'Android Release (Nexus 5X)':
            _chromium_gpu_spec(
                chromium_config='android',
                chromium_apply_config=[
                    'download_vr_test_apks',

                    # This is specified in order to match the same configuration
                    # in 'chromium.android:Marshmallow Phone Tester (rel)'.
                    'goma_high_parallel',
                    'mb',
                    'mb_luci_auth',
                ],
                gclient_config='chromium',
                gclient_apply_config=['android'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'android',
                },
                android_config='main_builder',
                bot_type=bot_spec.BUILDER_TESTER,
                testing={
                    'platform': 'linux',
                },
            ),
    },
}
