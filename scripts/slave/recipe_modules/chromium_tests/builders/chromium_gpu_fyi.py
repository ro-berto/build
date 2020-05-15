# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_spec


def _chromium_gpu_fyi_spec(**kwargs):
  if kwargs.get('bot_type') != bot_spec.DUMMY_TESTER:
    kwargs['build_gs_bucket'] = 'chromium-gpu-fyi-archive'
  return bot_spec.BotSpec.create(**kwargs)


SPEC = {
    'GPU FYI Win Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
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
            bot_type=bot_spec.BUILDER,
            simulation_platform='win',
        ),
    'GPU FYI Win Builder (dbg)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
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
                'TARGET_BITS': 32,
            },
            bot_type=bot_spec.BUILDER,
            simulation_platform='win',
        ),
    'GPU FYI Win dEQP Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
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
            bot_type=bot_spec.BUILDER,
            simulation_platform='win',
            # When trybots are set up which mirror this configuration,
            # compiling might induce a clobber build if the pinned
            # buildtools version is different from Chromium's default. This
            # is a risk we're willing to take because checkouts take a lot
            # of disk space, and this is expected to be a corner case rather
            # than the common case.
        ),
    'Win7 FYI Debug (AMD)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
            },
            bot_type=bot_spec.TESTER,
            parent_buildername='GPU FYI Win Builder (dbg)',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win7 FYI Release (AMD)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            bot_type=bot_spec.TESTER,
            parent_buildername='GPU FYI Win Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win7 FYI Release (NVIDIA)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            bot_type=bot_spec.TESTER,
            parent_buildername='GPU FYI Win Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win7 FYI dEQP Release (AMD)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            bot_type=bot_spec.TESTER,
            parent_buildername='GPU FYI Win dEQP Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'GPU FYI Win x64 Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
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
            bot_type=bot_spec.BUILDER,
            simulation_platform='win',
        ),
    'GPU FYI Win x64 Builder (dbg)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
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
            bot_type=bot_spec.BUILDER,
            simulation_platform='win',
        ),
    'GPU FYI Win x64 Builder DEPS ANGLE':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
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
            bot_type=bot_spec.BUILDER,
            simulation_platform='win',
        ),
    'GPU FYI Win x64 dEQP Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
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
            bot_type=bot_spec.BUILDER,
            simulation_platform='win',
            # When trybots are set up which mirror this configuration,
            # compiling might induce a clobber build if the pinned
            # buildtools version is different from Chromium's default. This
            # is a risk we're willing to take because checkouts take a lot
            # of disk space, and this is expected to be a corner case rather
            # than the common case.
        ),
    'GPU FYI Win x64 DX12 Vulkan Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
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
            bot_type=bot_spec.BUILDER,
            simulation_platform='win',
        ),
    'GPU FYI Win x64 DX12 Vulkan Builder (dbg)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
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
            bot_type=bot_spec.BUILDER,
            simulation_platform='win',
        ),
    'Win10 FYI x64 Debug (NVIDIA)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Win x64 Builder (dbg)',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win10 FYI x64 DX12 Vulkan Debug (NVIDIA)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Win x64 DX12 Vulkan Builder (dbg)',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win10 FYI x64 DX12 Vulkan Release (NVIDIA)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Win x64 DX12 Vulkan Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win10 FYI x64 Exp Release (Intel HD 630)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Win x64 Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win10 FYI x64 Exp Release (NVIDIA)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Win x64 Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win10 FYI x64 Release (AMD RX 550)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Win x64 Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win10 FYI x64 Release (Intel HD 630)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Win x64 Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win10 FYI x64 Release (Intel UHD 630)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Win x64 Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win10 FYI x64 Release (NVIDIA GeForce GTX 1660)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Win x64 Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win10 FYI x86 Release (NVIDIA)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            bot_type=bot_spec.TESTER,
            parent_buildername='GPU FYI Win Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win10 FYI x64 Release (NVIDIA)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Win x64 Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win10 FYI x64 SkiaRenderer Dawn Release (NVIDIA)':
        bot_spec.BotSpec.create(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win10 FYI x64 SkiaRenderer GL (NVIDIA)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Win x64 Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win10 FYI x64 dEQP Release (Intel HD 630)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Win x64 dEQP Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win10 FYI x64 dEQP Release (NVIDIA)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Win x64 dEQP Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win7 FYI x64 Release (NVIDIA)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Win x64 Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'Win7 FYI x64 dEQP Release (NVIDIA)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Win x64 dEQP Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'GPU FYI XR Win x64 Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
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
            bot_type=bot_spec.BUILDER,
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
                'mb_luci_auth',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.TESTER,
            parent_buildername='GPU FYI XR Win x64 Builder',
            simulation_platform='win',
            serialize_tests=True,
        ),
    'GPU FYI Linux Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
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
            bot_type=bot_spec.BUILDER,
            simulation_platform='linux',
        ),
    'GPU FYI Linux Builder DEPS ANGLE':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
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
            bot_type=bot_spec.BUILDER,
            simulation_platform='linux',
        ),
    'GPU FYI Linux Ozone Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
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
            bot_type=bot_spec.BUILDER,
            simulation_platform='linux',
        ),
    'GPU FYI Linux Builder (dbg)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
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
            bot_type=bot_spec.BUILDER,
            simulation_platform='linux',
        ),
    'GPU FYI Linux dEQP Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
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
            bot_type=bot_spec.BUILDER,
            simulation_platform='linux',
            # When trybots are set up which mirror this configuration,
            # compiling might induce a clobber build if the pinned
            # buildtools version is different from Chromium's default. This
            # is a risk we're willing to take because checkouts take a lot
            # of disk space, and this is expected to be a corner case rather
            # than the common case.
        ),
    'Linux FYI Release (NVIDIA)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Linux Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI Experimental Release (NVIDIA)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Linux Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI Debug (NVIDIA)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.TESTER,
            parent_buildername='GPU FYI Linux Builder (dbg)',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI dEQP Release (NVIDIA)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Linux dEQP Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI SkiaRenderer Vulkan (NVIDIA)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Linux Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI SkiaRenderer Vulkan (Intel HD 630)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Linux Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI Release (Intel HD 630)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Linux Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI Release (Intel UHD 630)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Linux Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI Experimental Release (Intel HD 630)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Linux Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI dEQP Release (Intel HD 630)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Linux dEQP Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI GPU TSAN Release':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb', 'mb_luci_auth'],
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
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI Release (AMD R7 240)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Linux Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Linux FYI SkiaRenderer Dawn Release (Intel HD 630)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'GPU FYI Fuchsia Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
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
            bot_type=bot_spec.BUILDER,
            simulation_platform='linux',
        ),
    'GPU FYI Mac Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
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
            bot_type=bot_spec.BUILDER,
            simulation_platform='mac',
        ),
    'GPU FYI Mac Builder DEPS ANGLE':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
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
            bot_type=bot_spec.BUILDER,
            simulation_platform='mac',
        ),
    'GPU FYI Mac Builder (dbg)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
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
            bot_type=bot_spec.BUILDER,
            simulation_platform='mac',
        ),
    'GPU FYI Mac dEQP Builder':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[],
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
            bot_type=bot_spec.BUILDER,
            simulation_platform='mac',
            # When trybots are set up which mirror this configuration,
            # compiling might induce a clobber build if the pinned
            # buildtools version is different from Chromium's default. This
            # is a risk we're willing to take because checkouts take a lot
            # of disk space, and this is expected to be a corner case rather
            # than the common case.
        ),
    'Mac FYI Release (Intel)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Mac Builder',
            simulation_platform='mac',
            serialize_tests=True,
        ),
    'Mac FYI Debug (Intel)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Mac Builder (dbg)',
            simulation_platform='mac',
            serialize_tests=True,
        ),
    'Mac Pro FYI Release (AMD)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Mac Builder',
            simulation_platform='mac',
            serialize_tests=True,
        ),
    'Mac FYI Retina Release (NVIDIA)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Mac Builder',
            simulation_platform='mac',
            serialize_tests=True,
        ),
    'Mac FYI Retina Debug (NVIDIA)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Mac Builder (dbg)',
            simulation_platform='mac',
            serialize_tests=True,
        ),
    'Mac FYI Retina Release (AMD)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Mac Builder',
            simulation_platform='mac',
            serialize_tests=True,
        ),
    'Mac FYI Retina Debug (AMD)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Mac Builder (dbg)',
            simulation_platform='mac',
            serialize_tests=True,
        ),
    'Mac FYI Experimental Release (Intel)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Mac Builder',
            simulation_platform='mac',
            serialize_tests=True,
        ),
    'Mac FYI Experimental Retina Release (AMD)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Mac Builder',
            simulation_platform='mac',
            serialize_tests=True,
        ),
    'Mac FYI Experimental Retina Release (NVIDIA)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Mac Builder',
            simulation_platform='mac',
            serialize_tests=True,
        ),
    'Mac FYI GPU ASAN Release':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb', 'mb_luci_auth'],
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
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='mac',
        ),
    'Mac FYI dEQP Release AMD':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[],
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
            bot_type=bot_spec.TESTER,
            parent_buildername='GPU FYI Mac dEQP Builder',
            simulation_platform='mac',
            serialize_tests=True,
        ),
    'Mac FYI dEQP Release Intel':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[],
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
            bot_type=bot_spec.TESTER,
            parent_buildername='GPU FYI Mac dEQP Builder',
            simulation_platform='mac',
            serialize_tests=True,
        ),
    'GPU FYI Perf Android 64 Builder':
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
            bot_type=bot_spec.BUILDER,
            simulation_platform='linux',
            # This causes the builder to upload isolates to a location where
            # Pinpoint can access them in addition to the usual isolate
            # server. This is necessary because "Android FYI 64 Perf (Pixel
            # 2)", which is a child of this builder, uploads perf results,
            # and Pinpoint may trigger additional builds on this builder
            # during a bisect.
            perf_isolate_upload=True,
        ),
    'Android FYI Release (Nexus 5)':
        _chromium_gpu_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb', 'mb_luci_auth'],
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
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'Android FYI Release (Nexus 5X)':
        _chromium_gpu_fyi_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
                'mb_luci_auth',
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
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'Android FYI Release (Nexus 6)':
        _chromium_gpu_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb', 'mb_luci_auth'],
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
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'Android FYI Release (Nexus 6P)':
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
            bot_type=bot_spec.BUILDER_TESTER,
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
            bot_type=bot_spec.BUILDER_TESTER,
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
            bot_type=bot_spec.BUILDER_TESTER,
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
            bot_type=bot_spec.BUILDER_TESTER,
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
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'Android FYI 32 Vk Release (Pixel 2)':
        _chromium_gpu_fyi_spec(
            chromium_config='android',
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
            android_config='main_builder_mb',
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'Android FYI 64 Vk Release (Pixel 2)':
        _chromium_gpu_fyi_spec(
            chromium_config='android',
            gclient_config='chromium',
            gclient_apply_config=[
                'android',
                'angle_internal',
                'angle_top_of_tree',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder_mb',
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'Android FYI 32 dEQP Vk Release (Pixel 2)':
        _chromium_gpu_fyi_spec(
            chromium_config='android',
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
            android_config='main_builder_mb',
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'Android FYI 64 dEQP Vk Release (Pixel 2)':
        _chromium_gpu_fyi_spec(
            chromium_config='android',
            gclient_config='chromium',
            gclient_apply_config=[
                'android',
                'angle_internal',
                'angle_top_of_tree',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder_mb',
            bot_type=bot_spec.BUILDER_TESTER,
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
            bot_type=bot_spec.BUILDER_TESTER,
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
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'Android FYI 64 Perf (Pixel 2)':
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
            bot_type=bot_spec.TESTER,
            parent_buildername='GPU FYI Perf Android 64 Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'ChromeOS FYI Release (amd64-generic)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
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
                'TARGET_CROS_BOARD': 'amd64-generic',
                'TARGET_PLATFORM': 'chromeos',
            },
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'ChromeOS FYI Release (kevin)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
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
                'TARGET_CROS_BOARD': 'kevin',
                'TARGET_PLATFORM': 'chromeos',
            },
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'GPU Fake Linux Builder':
        _chromium_gpu_fyi_spec(
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
            simulation_platform='linux',
        ),
    'Fake Linux Release (NVIDIA)':
        _chromium_gpu_fyi_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb', 'mb_luci_auth'],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            },
            bot_type=bot_spec.TESTER,
            parent_buildername='GPU Fake Linux Builder',
            simulation_platform='linux',
        ),
    'Linux FYI Ozone (Intel)':
        _chromium_gpu_fyi_spec(
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
            parent_buildername='GPU FYI Linux Ozone Builder',
            simulation_platform='linux',
            serialize_tests=True,
        ),

    # The following machines don't actually exist. They are specified
    # here only in order to allow the associated src-side JSON entries
    # to be read, and the "optional" GPU tryservers to be specified in
    # terms of them.
    'Optional Win10 x64 Release (NVIDIA)':
        _chromium_gpu_fyi_spec(bot_type=bot_spec.DUMMY_TESTER),
    'Optional Win10 x64 Release (Intel HD 630)':
        _chromium_gpu_fyi_spec(bot_type=bot_spec.DUMMY_TESTER),
    'Optional Linux Release (NVIDIA)':
        _chromium_gpu_fyi_spec(bot_type=bot_spec.DUMMY_TESTER),
    'Optional Linux Release (Intel HD 630)':
        _chromium_gpu_fyi_spec(bot_type=bot_spec.DUMMY_TESTER),
    'Optional Mac Release (Intel)':
        _chromium_gpu_fyi_spec(bot_type=bot_spec.DUMMY_TESTER),
    'Optional Mac Retina Release (NVIDIA)':
        _chromium_gpu_fyi_spec(bot_type=bot_spec.DUMMY_TESTER),
    'Optional Mac Retina Release (AMD)':
        _chromium_gpu_fyi_spec(bot_type=bot_spec.DUMMY_TESTER),
    'Optional Android Release (Nexus 5X)':
        _chromium_gpu_fyi_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
                # This is specified in order to match the same configuration
                # in 'chromium.android:Marshmallow Phone Tester (rel)'.
                'goma_high_parallel',
            ],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder_mb',
            bot_type=bot_spec.BUILDER_TESTER,
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
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'ANGLE GPU Linux Release (NVIDIA)':
        _chromium_gpu_fyi_spec(bot_type=bot_spec.DUMMY_TESTER),
    'ANGLE GPU Linux Release (Intel HD 630)':
        _chromium_gpu_fyi_spec(bot_type=bot_spec.DUMMY_TESTER),
    'ANGLE GPU Mac Release (Intel)':
        _chromium_gpu_fyi_spec(bot_type=bot_spec.DUMMY_TESTER),
    'ANGLE GPU Mac Retina Release (NVIDIA)':
        _chromium_gpu_fyi_spec(bot_type=bot_spec.DUMMY_TESTER),
    'ANGLE GPU Mac Retina Release (AMD)':
        _chromium_gpu_fyi_spec(bot_type=bot_spec.DUMMY_TESTER),
    'ANGLE GPU Win10 x64 Release (NVIDIA)':
        _chromium_gpu_fyi_spec(bot_type=bot_spec.DUMMY_TESTER),
    'ANGLE GPU Win10 x64 Release (Intel HD 630)':
        _chromium_gpu_fyi_spec(bot_type=bot_spec.DUMMY_TESTER),
    'Win7 ANGLE Tryserver (AMD)':
        _chromium_gpu_fyi_spec(bot_type=bot_spec.DUMMY_TESTER),
}
