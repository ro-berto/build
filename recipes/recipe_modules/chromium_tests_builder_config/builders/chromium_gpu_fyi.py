# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec


def _chromium_gpu_fyi_spec(**kwargs):
  if kwargs.get('execution_mode') != builder_spec.PROVIDE_TEST_SPEC:
    kwargs.setdefault('build_gs_bucket', 'chromium-gpu-fyi-archive')
    kwargs.setdefault('isolate_server', 'https://isolateserver.appspot.com')
  return builder_spec.BuilderSpec.create(**kwargs)


SPEC = {
    'GPU FYI Win Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'chrome_internal',
                'angle_internal',
                'angle_top_of_tree',
                'no_kaleidoscope',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            simulation_platform='win',
        ),
    'Win7 FYI Release (AMD)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Win Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win7 FYI Release (NVIDIA)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Win Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'GPU FYI Win x64 Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'chrome_internal',
                'angle_internal',
                'angle_top_of_tree',
                'no_kaleidoscope',
            ],
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
            gclient_apply_config=[
                'chrome_internal',
                'angle_internal',
                'angle_top_of_tree',
                'no_kaleidoscope',
            ],
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
                'chrome_internal',
                'angle_internal',
                'no_kaleidoscope',
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
            gclient_apply_config=[
                'chrome_internal',
                'angle_internal',
                'angle_top_of_tree',
                'no_kaleidoscope',
            ],
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
            gclient_apply_config=[
                'chrome_internal',
                'angle_internal',
                'angle_top_of_tree',
                'no_kaleidoscope',
            ],
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
    'Win10 FYI x64 Release (NVIDIA GeForce GTX 1660)':
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
    'Win10 FYI x86 Release (NVIDIA)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Win Builder',
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
    'Win10 FYI x64 SkiaRenderer Dawn Release (NVIDIA)':
        builder_spec.BuilderSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win7 FYI x64 Release (NVIDIA)':
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
            gclient_apply_config=[
                'chrome_internal',
                'angle_internal',
                'angle_top_of_tree',
                'no_kaleidoscope',
            ],
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
    'GPU FYI Linux Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'chrome_internal',
                'angle_internal',
                'angle_top_of_tree',
                'no_kaleidoscope',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'GPU FYI Linux Builder DEPS ANGLE':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'chrome_internal',
                'angle_internal',
                'no_kaleidoscope',
            ],
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
            gclient_apply_config=[
                'chrome_internal',
                'angle_internal',
                'angle_top_of_tree',
                'no_kaleidoscope',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
        ),
    'GPU FYI Linux dEQP Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'chrome_internal',
                'angle_internal',
                'angle_top_of_tree',
                'no_kaleidoscope',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
            # When trybots are set up which mirror this configuration,
            # compiling might induce a clobber build if the pinned
            # buildtools version is different from Chromium's default. This
            # is a risk we're willing to take because checkouts take a lot
            # of disk space, and this is expected to be a corner case rather
            # than the common case.
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
    'Linux FYI Release (NVIDIA)':
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
            parent_buildername='GPU FYI Linux Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI Experimental Release (NVIDIA)':
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
            parent_buildername='GPU FYI Linux Builder',
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
    'Linux FYI dEQP Release (NVIDIA)':
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
            parent_buildername='GPU FYI Linux dEQP Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI SkiaRenderer Vulkan (NVIDIA)':
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
            parent_buildername='GPU FYI Linux Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI SkiaRenderer Vulkan (Intel HD 630)':
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
            parent_buildername='GPU FYI Linux Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI Release (Intel HD 630)':
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
            parent_buildername='GPU FYI Linux Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI Release (Intel UHD 630)':
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
            parent_buildername='GPU FYI Linux Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI Experimental Release (Intel HD 630)':
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
            parent_buildername='GPU FYI Linux Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI dEQP Release (Intel HD 630)':
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
            parent_buildername='GPU FYI Linux dEQP Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI GPU TSAN Release':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=[
                'chrome_internal',
                'angle_internal',
                'angle_top_of_tree',
                'no_kaleidoscope',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI Release (AMD RX 5500 XT)':
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
            parent_buildername='GPU FYI Linux Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI SkiaRenderer Dawn Release (Intel HD 630)':
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
    'GPU FYI Fuchsia Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'chrome_internal',
                'angle_internal',
                'angle_top_of_tree',
                'fuchsia',
                'no_kaleidoscope',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'fuchsia',
            },
            simulation_platform='linux',
        ),
    'GPU FYI Mac Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'chrome_internal',
                'angle_internal',
                'angle_top_of_tree',
                'no_kaleidoscope',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
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
                'chrome_internal',
                'angle_internal',
                'no_kaleidoscope',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
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
            gclient_apply_config=[
                'chrome_internal',
                'angle_internal',
                'angle_top_of_tree',
                'no_kaleidoscope',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            simulation_platform='mac',
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
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Mac Builder',
            simulation_platform='mac',
            serialize_tests=True,
        ),
    'Mac FYI Release (Intel UHD 630)':
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
            parent_buildername='GPU FYI Mac Builder',
            simulation_platform='mac',
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
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Mac Builder (dbg)',
            simulation_platform='mac',
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
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Mac Builder',
            simulation_platform='mac',
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
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Mac Builder',
            simulation_platform='mac',
            serialize_tests=True,
        ),
    'Mac FYI Retina Debug (NVIDIA)':
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
            parent_buildername='GPU FYI Mac Builder (dbg)',
            simulation_platform='mac',
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
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Mac Builder',
            simulation_platform='mac',
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
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Mac Builder (dbg)',
            simulation_platform='mac',
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
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Mac Builder',
            simulation_platform='mac',
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
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Mac Builder',
            simulation_platform='mac',
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
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='GPU FYI Mac Builder',
            simulation_platform='mac',
            serialize_tests=True,
        ),
    'Mac FYI GPU ASAN Release':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=[
                'chrome_internal',
                'angle_internal',
                'angle_top_of_tree',
                'no_kaleidoscope',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            simulation_platform='mac',
        ),
    'Mac FYI arm64 Release (Apple DTK)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'chrome_internal',
                'angle_internal',
                'angle_top_of_tree',
                'no_kaleidoscope',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            },
            simulation_platform='mac',
            serialize_tests=True,
        ),
    'Android FYI Release (Nexus 5)':
        _chromium_gpu_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=[
                'android',
                'angle_internal',
                'angle_top_of_tree',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            simulation_platform='linux',
        ),
    'Android FYI Release (Nexus 5X)':
        _chromium_gpu_fyi_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'android',
                'angle_internal',
                'angle_top_of_tree',
            ],
            chromium_config_kwargs={
                'TARGET_PLATFORM': 'android',
            },
            android_config='arm64_builder_rel_mb',
            simulation_platform='linux',
        ),
    'Android FYI Release (Nexus 6)':
        _chromium_gpu_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=[
                'android',
                'angle_internal',
                'angle_top_of_tree',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            simulation_platform='linux',
        ),
    'Android FYI Release (Nexus 9)':
        _chromium_gpu_fyi_spec(
            chromium_config='android',
            gclient_config='chromium',
            gclient_apply_config=[
                'android',
                'angle_internal',
                'angle_top_of_tree',
            ],
            chromium_config_kwargs={
                'TARGET_PLATFORM': 'android',
            },
            android_config='arm64_builder_rel_mb',
            simulation_platform='linux',
        ),
    'Android FYI Release (NVIDIA Shield TV)':
        _chromium_gpu_fyi_spec(
            chromium_config='android',
            gclient_config='chromium',
            gclient_apply_config=[
                'android',
                'angle_internal',
                'angle_top_of_tree',
            ],
            chromium_config_kwargs={
                'TARGET_PLATFORM': 'android',
            },
            android_config='arm64_builder_rel_mb',
            simulation_platform='linux',
        ),
    'Android FYI Release (Pixel 2)':
        _chromium_gpu_fyi_spec(
            chromium_config='android',
            gclient_config='chromium',
            gclient_apply_config=[
                'android',
                'angle_internal',
                'angle_top_of_tree',
            ],
            chromium_config_kwargs={
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            simulation_platform='linux',
        ),
    'Android FYI Release (Pixel 4)':
        _chromium_gpu_fyi_spec(
            chromium_config='android',
            gclient_config='chromium',
            gclient_apply_config=[
                'android',
            ],
            chromium_config_kwargs={
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            simulation_platform='linux',
        ),
    'Android FYI dEQP Release (Nexus 5X)':
        _chromium_gpu_fyi_spec(
            chromium_config='android',
            gclient_config='chromium',
            gclient_apply_config=[
                'android',
                'angle_internal',
                'angle_top_of_tree',
            ],
            chromium_config_kwargs={
                'TARGET_PLATFORM': 'android',
            },
            android_config='arm64_builder_rel_mb',
            simulation_platform='linux',
        ),
    'Android FYI SkiaRenderer GL (Nexus 5X)':
        _chromium_gpu_fyi_spec(
            chromium_config='android',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder_mb',
            simulation_platform='linux',
        ),
    'Android FYI SkiaRenderer Vulkan (Pixel 2)':
        _chromium_gpu_fyi_spec(
            chromium_config='android',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder_mb',
            simulation_platform='linux',
        ),
    'ChromeOS FYI Release (amd64-generic)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'angle_top_of_tree',
                'chromeos',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 64,
                'CROS_BOARDS_WITH_QEMU_IMAGES': 'amd64-generic',
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
                'angle_top_of_tree',
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

    # The following machines don't actually exist. They are specified
    # here only in order to allow the associated src-side JSON entries
    # to be read, and the "optional" GPU tryservers to be specified in
    # terms of them.
    'Optional Win10 x64 Release (NVIDIA)':
        _chromium_gpu_fyi_spec(execution_mode=builder_spec.PROVIDE_TEST_SPEC),
    'Optional Win10 x64 Release (Intel HD 630)':
        _chromium_gpu_fyi_spec(execution_mode=builder_spec.PROVIDE_TEST_SPEC),
    'Optional Linux Release (NVIDIA)':
        _chromium_gpu_fyi_spec(execution_mode=builder_spec.PROVIDE_TEST_SPEC),
    'Optional Linux Release (Intel HD 630)':
        _chromium_gpu_fyi_spec(execution_mode=builder_spec.PROVIDE_TEST_SPEC),
    'Optional Mac Release (Intel)':
        _chromium_gpu_fyi_spec(execution_mode=builder_spec.PROVIDE_TEST_SPEC),
    'Optional Mac Retina Release (NVIDIA)':
        _chromium_gpu_fyi_spec(execution_mode=builder_spec.PROVIDE_TEST_SPEC),
    'Optional Mac Retina Release (AMD)':
        _chromium_gpu_fyi_spec(execution_mode=builder_spec.PROVIDE_TEST_SPEC),
    'Optional Android Release (Pixel 4)':
        _chromium_gpu_fyi_spec(
            chromium_config='android',
            gclient_config='chromium',
            gclient_apply_config=[
                'android',
            ],
            chromium_config_kwargs={
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            simulation_platform='linux',
        ),

    # This following machines don't exist either; they are separate
    # configurations because we don't have the capacity to run all of
    # the tests on the GPU try servers. And to specify tests for
    # ANGLE's try servers separately from the gpu.fyi waterfall.
    'ANGLE GPU Android Release (Nexus 5X)':
        _chromium_gpu_fyi_spec(
            chromium_config='android',
            gclient_config='chromium',
            gclient_apply_config=[
                'android',
                'angle_internal',
                'angle_top_of_tree',
            ],
            chromium_config_kwargs={
                'TARGET_PLATFORM': 'android',
            },
            android_config='arm64_builder_rel_mb',
            simulation_platform='linux',
        ),
    'ANGLE GPU Linux Release (NVIDIA)':
        _chromium_gpu_fyi_spec(execution_mode=builder_spec.PROVIDE_TEST_SPEC),
    'ANGLE GPU Linux Release (Intel HD 630)':
        _chromium_gpu_fyi_spec(execution_mode=builder_spec.PROVIDE_TEST_SPEC),
}
