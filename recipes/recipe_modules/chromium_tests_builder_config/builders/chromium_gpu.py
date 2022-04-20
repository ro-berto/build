# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec


def _chromium_gpu_spec(**kwargs):
  return builder_spec.BuilderSpec.create(
      build_gs_bucket='chromium-gpu-archive', **kwargs)

# The config for the following builders is now specified src-side in
# //infra/config/subprojects/chromium/ci/chromium.gpu.star
# * GPU Mac Builder
# * GPU Win x64 Builder
# * Mac Release (Intel)
# * Mac Retina Release (AMD)
# * Win10 x64 Release (NVIDIA)

SPEC = {
    'GPU Win x64 Builder (dbg)':
        _chromium_gpu_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            simulation_platform='win',
        ),
    'Win10 x64 Debug (NVIDIA)':
        _chromium_gpu_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU Win x64 Builder (dbg)',
            simulation_platform='win',
        ),
    'GPU Linux Builder':
        _chromium_gpu_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'use_clang_coverage',
                'enable_reclient',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'GPU Linux Builder (dbg)':
        _chromium_gpu_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'enable_reclient',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'Linux Release (NVIDIA)':
        _chromium_gpu_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=['use_clang_coverage'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU Linux Builder',
            simulation_platform='linux',
        ),
    'Linux Debug (NVIDIA)':
        _chromium_gpu_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU Linux Builder (dbg)',
            simulation_platform='linux',
        ),
    'GPU Mac Builder (dbg)':
        _chromium_gpu_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'mac',
            },
            simulation_platform='mac',
        ),
    'Mac Debug (Intel)':
        _chromium_gpu_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'mac',
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU Mac Builder (dbg)',
            simulation_platform='linux',
        ),
    'Mac Retina Debug (AMD)':
        _chromium_gpu_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'mac',
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU Mac Builder (dbg)',
            simulation_platform='linux',
        ),
    'Android Release (Nexus 5X)':
        _chromium_gpu_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'android',
                'enable_reclient',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            simulation_platform='linux',
        ),
}
