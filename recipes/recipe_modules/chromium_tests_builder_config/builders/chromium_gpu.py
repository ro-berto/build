# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec


def _chromium_gpu_spec(**kwargs):
  return builder_spec.BuilderSpec.create(
      build_gs_bucket='chromium-gpu-archive', **kwargs)

# The config for the following builders is now specified src-side in
# //infra/config/subprojects/chromium/ci/chromium.gpu.star
# * Android Release (Nexus 5X)
# * GPU Linux Builder
# * GPU Linux Builder (dbg)
# * GPU Mac Builder
# * GPU Win x64 Builder
# * GPU Win x64 Builder (dbg)
# * Linux Debug (NVIDIA)
# * Linux Release (NVIDIA)
# * Mac Release (Intel)
# * Mac Retina Release (AMD)
# * Win10 x64 Debug (NVIDIA)
# * Win10 x64 Release (NVIDIA)

SPEC = {
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
}
