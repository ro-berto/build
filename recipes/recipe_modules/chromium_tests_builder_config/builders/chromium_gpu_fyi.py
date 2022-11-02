# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec


def _chromium_gpu_fyi_spec(build_gs_bucket='chromium-gpu-fyi-archive',
                           **kwargs):
  return builder_spec.BuilderSpec.create(**kwargs)

# The config for the following virtual builders were removed since their trybot
# mirrors were migrated src-side:
# * Android FYI Release (Nexus 5)
# * Android FYI Release (Nexus 5X)
# * Android FYI Release (NVIDIA Shield TV)
# * Android FYI Release (Pixel 2)
# * Android FYI Release (Pixel 4)
# * Android FYI Release (Pixel 6)
# * GPU FYI Android arm Builder
# * GPU FYI Android arm64 Builder
# * GPU FYI Linux Builder
# * GPU FYI Linux Builder DEPS ANGLE
# * GPU FYI Win Builder
# * Linux FYI Experimental Release (Intel HD 630)
# * Linux FYI Experimental Release (NVIDIA)
# * Linux FYI Release (AMD RX 5500 XT)
# * Linux FYI Release (Intel HD 630)
# * Linux FYI Release (Intel UHD 630)
# * Linux FYI Release (NVIDIA)
# * Optional Linux Release (Intel HD 630)
# * Optional Linux Release (NVIDIA)
# * Win10 FYI x86 Release (NVIDIA)

SPEC = {
    'GPU FYI Win x64 Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='win',
        ),
    'GPU FYI Win x64 Builder (dbg)':
        _chromium_gpu_fyi_spec(
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
    'GPU FYI Win x64 Builder DEPS ANGLE':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'angle_internal',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='win',
        ),
    'GPU FYI Win x64 DX12 Vulkan Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='win',
        ),
    'GPU FYI Win x64 DX12 Vulkan Builder (dbg)':
        _chromium_gpu_fyi_spec(
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
    'Win10 FYI x64 Debug (NVIDIA)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Win x64 Builder (dbg)',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win10 FYI x64 DX12 Vulkan Debug (NVIDIA)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Win x64 DX12 Vulkan Builder (dbg)',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win10 FYI x64 DX12 Vulkan Release (NVIDIA)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Win x64 DX12 Vulkan Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win10 FYI x64 Exp Release (Intel HD 630)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Win x64 Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win10 FYI x64 Exp Release (NVIDIA)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Win x64 Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win10 FYI x64 Release (AMD RX 5500 XT)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Win x64 Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win10 FYI x64 Release (Intel HD 630)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Win x64 Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win10 FYI x64 Release (NVIDIA)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Win x64 Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'GPU FYI XR Win x64 Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='win',
            # This causes the builder to upload isolates to a location where
            # Pinpoint can access them in addition to the usual isolate
            # server. This is necessary because "Win10 FYI x64 Release XR
            # perf (NVIDIA)", which is a child of this builder, uploads perf
            # results, and Pinpoint may trigger additional builds on this
            # builder during a bisect.
            perf_isolate_upload=True,
        ),
    'Win10 FYI x64 Release XR Perf (NVIDIA)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI XR Win x64 Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'GPU FYI Lacros x64 Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'GPU FYI Linux Builder (dbg)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'Lacros FYI x64 Release (AMD)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Lacros x64 Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Lacros FYI x64 Release (Intel)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Lacros x64 Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI Debug (NVIDIA)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Linux Builder (dbg)',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI GPU TSAN Release':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'GPU FYI Mac Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'mac',
            },
            simulation_platform='mac',
        ),
    'GPU FYI Mac Builder DEPS ANGLE':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'angle_internal',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='mac',
        ),
    'GPU FYI Mac Builder (asan)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'mac',
            },
            simulation_platform='mac',
        ),
    'GPU FYI Mac Builder (dbg)':
        _chromium_gpu_fyi_spec(
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
    'Mac FYI ASAN (Intel)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'mac',
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Mac Builder (asan)',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Mac FYI Release (Intel)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'mac',
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Mac Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Mac FYI Debug (Intel)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Mac Builder (dbg)',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Mac Pro FYI Release (AMD)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'mac',
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Mac Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Mac FYI Retina Release (NVIDIA)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'mac',
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Mac Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Mac FYI Retina ASAN (AMD)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'mac',
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Mac Builder (asan)',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Mac FYI Retina Release (AMD)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'mac',
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Mac Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Mac FYI Retina Debug (AMD)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Mac Builder (dbg)',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Mac FYI Experimental Release (Intel)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'mac',
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Mac Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Mac FYI Experimental Retina Release (AMD)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'mac',
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Mac Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Mac FYI Experimental Retina Release (NVIDIA)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'mac',
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Mac Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'ChromeOS FYI Release (amd64-generic)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'chromeos',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 64,
                'CROS_BOARDS_WITH_QEMU_IMAGES': 'amd64-generic-vm',
                'TARGET_PLATFORM': 'chromeos',
            },
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'gpu-fyi-chromeos-jacuzzi-exp':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'arm',
                'chromeos',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 32,
                'TARGET_CROS_BOARDS': 'jacuzzi',
                'TARGET_PLATFORM': 'chromeos',
            },
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'ChromeOS FYI Release (kevin)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'arm',
                'chromeos',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 32,
                'TARGET_CROS_BOARDS': 'kevin',
                'TARGET_PLATFORM': 'chromeos',
            },
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'gpu-fyi-chromeos-octopus-exp':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'chromeos',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 64,
                'TARGET_CROS_BOARDS': 'octopus',
                'TARGET_PLATFORM': 'chromeos',
            },
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'GPU Fake Linux Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'Fake Linux Release (NVIDIA)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU Fake Linux Builder',
            simulation_platform='linux',
        ),
}
