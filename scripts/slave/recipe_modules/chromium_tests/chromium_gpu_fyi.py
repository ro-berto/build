# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import bot_spec

SPEC = {
    'settings': {
        'build_gs_bucket': 'chromium-gpu-fyi-archive',
    },
    'builders': {
        'GPU FYI Win Builder':
            bot_spec.BotSpec.create(
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
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'win',
                },
            ),
        'GPU FYI Win Builder (dbg)':
            bot_spec.BotSpec.create(
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
                    'TARGET_BITS': 32,
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'win',
                },
            ),
        'GPU FYI Win dEQP Builder':
            bot_spec.BotSpec.create(
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
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'win',
                },
                # When trybots are set up which mirror this configuration,
                # compiling might induce a clobber build if the pinned
                # buildtools version is different from Chromium's default. This
                # is a risk we're willing to take because checkouts take a lot
                # of disk space, and this is expected to be a corner case rather
                # than the common case.
            ),
        'Win7 FYI Debug (AMD)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 32,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Win Builder (dbg)',
                testing={
                    'platform': 'win',
                },
                serialize_tests=True,
            ),
        'Win7 FYI Release (AMD)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Win Builder',
                testing={
                    'platform': 'win',
                },
                serialize_tests=True,
            ),
        'Win7 FYI Release (NVIDIA)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Win Builder',
                testing={
                    'platform': 'win',
                },
                serialize_tests=True,
            ),
        'Win7 FYI dEQP Release (AMD)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Win dEQP Builder',
                testing={
                    'platform': 'win',
                },
                serialize_tests=True,
            ),
        'GPU FYI Win x64 Builder':
            bot_spec.BotSpec.create(
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
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'win',
                },
            ),
        'GPU FYI Win x64 Builder (dbg)':
            bot_spec.BotSpec.create(
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
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'win',
                },
            ),
        'GPU FYI Win x64 Builder DEPS ANGLE':
            bot_spec.BotSpec.create(
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
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'win',
                },
            ),
        'GPU FYI Win x64 dEQP Builder':
            bot_spec.BotSpec.create(
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
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'win',
                },
                # When trybots are set up which mirror this configuration,
                # compiling might induce a clobber build if the pinned
                # buildtools version is different from Chromium's default. This
                # is a risk we're willing to take because checkouts take a lot
                # of disk space, and this is expected to be a corner case rather
                # than the common case.
            ),
        'GPU FYI Win x64 DX12 Vulkan Builder':
            bot_spec.BotSpec.create(
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
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'win',
                },
            ),
        'GPU FYI Win x64 DX12 Vulkan Builder (dbg)':
            bot_spec.BotSpec.create(
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
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'win',
                },
            ),
        'Win10 FYI x64 Debug (NVIDIA)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Win x64 Builder (dbg)',
                testing={
                    'platform': 'win',
                },
                serialize_tests=True,
            ),
        'Win10 FYI x64 DX12 Vulkan Debug (NVIDIA)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Win x64 DX12 Vulkan Builder (dbg)',
                testing={
                    'platform': 'win',
                },
                serialize_tests=True,
            ),
        'Win10 FYI x64 DX12 Vulkan Release (NVIDIA)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Win x64 DX12 Vulkan Builder',
                testing={
                    'platform': 'win',
                },
                serialize_tests=True,
            ),
        'Win10 FYI x64 Exp Release (Intel HD 630)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Win x64 Builder',
                testing={
                    'platform': 'win',
                },
                serialize_tests=True,
            ),
        'Win10 FYI x64 Exp Release (NVIDIA)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Win x64 Builder',
                testing={
                    'platform': 'win',
                },
                serialize_tests=True,
            ),
        'Win10 FYI x64 Release (AMD RX 550)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Win x64 Builder',
                testing={
                    'platform': 'win',
                },
                serialize_tests=True,
            ),
        'Win10 FYI x64 Release (Intel HD 630)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Win x64 Builder',
                testing={
                    'platform': 'win',
                },
                serialize_tests=True,
            ),
        'Win10 FYI x64 Release (Intel UHD 630)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Win x64 Builder',
                testing={
                    'platform': 'win',
                },
                serialize_tests=True,
            ),
        'Win10 FYI x64 Release (NVIDIA GeForce GTX 1660)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Win x64 Builder',
                testing={
                    'platform': 'win',
                },
                serialize_tests=True,
            ),
        'Win10 FYI x86 Release (NVIDIA)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Win Builder',
                testing={
                    'platform': 'win',
                },
                serialize_tests=True,
            ),
        'Win10 FYI x64 Release (NVIDIA)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Win x64 Builder',
                testing={
                    'platform': 'win',
                },
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
                testing={
                    'platform': 'win',
                },
                serialize_tests=True,
            ),
        'Win10 FYI x64 SkiaRenderer GL (NVIDIA)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Win x64 Builder',
                testing={
                    'platform': 'win',
                },
                serialize_tests=True,
            ),
        'Win10 FYI x64 dEQP Release (Intel HD 630)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Win x64 dEQP Builder',
                testing={
                    'platform': 'win',
                },
                serialize_tests=True,
            ),
        'Win10 FYI x64 dEQP Release (NVIDIA)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Win x64 dEQP Builder',
                testing={
                    'platform': 'win',
                },
                serialize_tests=True,
            ),
        'Win7 FYI x64 Release (NVIDIA)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Win x64 Builder',
                testing={
                    'platform': 'win',
                },
                serialize_tests=True,
            ),
        'Win7 FYI x64 dEQP Release (NVIDIA)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Win x64 dEQP Builder',
                testing={
                    'platform': 'win',
                },
                serialize_tests=True,
            ),
        'GPU FYI XR Win x64 Builder':
            bot_spec.BotSpec.create(
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
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'win',
                },
                # This causes the builder to upload isolates to a location where
                # Pinpoint can access them in addition to the usual isolate
                # server. This is necessary because "Win10 FYI x64 Release XR
                # perf (NVIDIA)", which is a child of this builder, uploads perf
                # results, and Pinpoint may trigger additional builds on this
                # builder during a bisect.
                perf_isolate_lookup=True,
            ),
        'Win10 FYI x64 Release XR Perf (NVIDIA)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI XR Win x64 Builder',
                testing={
                    'platform': 'win',
                },
                serialize_tests=True,
            ),
        'GPU FYI Linux Builder':
            bot_spec.BotSpec.create(
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
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'linux',
                },
            ),
        'GPU FYI Linux Builder DEPS ANGLE':
            bot_spec.BotSpec.create(
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
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'linux',
                },
            ),
        'GPU FYI Linux Ozone Builder':
            bot_spec.BotSpec.create(
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
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'linux',
                },
            ),
        'GPU FYI Linux Builder (dbg)':
            bot_spec.BotSpec.create(
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
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'linux',
                },
            ),
        'GPU FYI Linux dEQP Builder':
            bot_spec.BotSpec.create(
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
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'linux',
                },
                # When trybots are set up which mirror this configuration,
                # compiling might induce a clobber build if the pinned
                # buildtools version is different from Chromium's default. This
                # is a risk we're willing to take because checkouts take a lot
                # of disk space, and this is expected to be a corner case rather
                # than the common case.
            ),
        'Linux FYI Release (NVIDIA)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Linux Builder',
                testing={
                    'platform': 'linux',
                },
                serialize_tests=True,
            ),
        'Linux FYI Experimental Release (NVIDIA)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Linux Builder',
                testing={
                    'platform': 'linux',
                },
                serialize_tests=True,
            ),
        'Linux FYI Debug (NVIDIA)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Linux Builder (dbg)',
                testing={
                    'platform': 'linux',
                },
                serialize_tests=True,
            ),
        'Linux FYI dEQP Release (NVIDIA)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Linux dEQP Builder',
                testing={
                    'platform': 'linux',
                },
                serialize_tests=True,
            ),
        'Linux FYI SkiaRenderer Vulkan (NVIDIA)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Linux Builder',
                testing={
                    'platform': 'linux',
                },
                serialize_tests=True,
            ),
        'Linux FYI SkiaRenderer Vulkan (Intel HD 630)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Linux Builder',
                testing={
                    'platform': 'linux',
                },
                serialize_tests=True,
            ),
        'Linux FYI Release (Intel HD 630)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Linux Builder',
                testing={
                    'platform': 'linux',
                },
                serialize_tests=True,
            ),
        'Linux FYI Release (Intel UHD 630)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Linux Builder',
                testing={
                    'platform': 'linux',
                },
                serialize_tests=True,
            ),
        'Linux FYI Experimental Release (Intel HD 630)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Linux Builder',
                testing={
                    'platform': 'linux',
                },
                serialize_tests=True,
            ),
        'Linux FYI dEQP Release (Intel HD 630)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Linux dEQP Builder',
                testing={
                    'platform': 'linux',
                },
                serialize_tests=True,
            ),
        'Linux FYI GPU TSAN Release':
            bot_spec.BotSpec.create(
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
                bot_type=bot_spec.BUILDER_TESTER,
                testing={
                    'platform': 'linux',
                },
                serialize_tests=True,
            ),
        'Linux FYI Release (AMD R7 240)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Linux Builder',
                testing={
                    'platform': 'linux',
                },
                serialize_tests=True,
            ),
        'Linux FYI SkiaRenderer Dawn Release (Intel HD 630)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER_TESTER,
                testing={
                    'platform': 'linux',
                },
                serialize_tests=True,
            ),
        'GPU FYI Fuchsia Builder':
            bot_spec.BotSpec.create(
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
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'linux',
                },
            ),
        'GPU FYI Mac Builder':
            bot_spec.BotSpec.create(
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
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'mac',
                },
            ),
        'GPU FYI Mac Builder DEPS ANGLE':
            bot_spec.BotSpec.create(
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
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'mac',
                },
            ),
        'GPU FYI Mac Builder (dbg)':
            bot_spec.BotSpec.create(
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
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'mac',
                },
            ),
        'GPU FYI Mac dEQP Builder':
            bot_spec.BotSpec.create(
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
                testing={
                    'platform': 'mac',
                },
                # When trybots are set up which mirror this configuration,
                # compiling might induce a clobber build if the pinned
                # buildtools version is different from Chromium's default. This
                # is a risk we're willing to take because checkouts take a lot
                # of disk space, and this is expected to be a corner case rather
                # than the common case.
            ),
        'Mac FYI Release (Intel)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Mac Builder',
                testing={
                    'platform': 'mac',
                },
                serialize_tests=True,
            ),
        'Mac FYI Debug (Intel)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Mac Builder (dbg)',
                testing={
                    'platform': 'mac',
                },
                serialize_tests=True,
            ),
        'Mac Pro FYI Release (AMD)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Mac Builder',
                testing={
                    'platform': 'mac',
                },
                serialize_tests=True,
            ),
        'Mac FYI Retina Release (NVIDIA)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Mac Builder',
                testing={
                    'platform': 'mac',
                },
                serialize_tests=True,
            ),
        'Mac FYI Retina Debug (NVIDIA)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Mac Builder (dbg)',
                testing={
                    'platform': 'mac',
                },
                serialize_tests=True,
            ),
        'Mac FYI Retina Release (AMD)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Mac Builder',
                testing={
                    'platform': 'mac',
                },
                serialize_tests=True,
            ),
        'Mac FYI Retina Debug (AMD)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Mac Builder (dbg)',
                testing={
                    'platform': 'mac',
                },
                serialize_tests=True,
            ),
        'Mac FYI Experimental Release (Intel)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Mac Builder',
                testing={
                    'platform': 'mac',
                },
                serialize_tests=True,
            ),
        'Mac FYI Experimental Retina Release (AMD)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Mac Builder',
                testing={
                    'platform': 'mac',
                },
                serialize_tests=True,
            ),
        'Mac FYI Experimental Retina Release (NVIDIA)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Mac Builder',
                testing={
                    'platform': 'mac',
                },
                serialize_tests=True,
            ),
        'Mac FYI GPU ASAN Release':
            bot_spec.BotSpec.create(
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
                bot_type=bot_spec.BUILDER_TESTER,
                testing={
                    'platform': 'mac',
                },
            ),
        'Mac FYI dEQP Release AMD':
            bot_spec.BotSpec.create(
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
                testing={
                    'platform': 'mac',
                },
                serialize_tests=True,
            ),
        'Mac FYI dEQP Release Intel':
            bot_spec.BotSpec.create(
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
                testing={
                    'platform': 'mac',
                },
                serialize_tests=True,
            ),
        'GPU FYI Perf Android 64 Builder':
            bot_spec.BotSpec.create(
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
                testing={
                    'platform': 'linux',
                },
                # This causes the builder to upload isolates to a location where
                # Pinpoint can access them in addition to the usual isolate
                # server. This is necessary because "Android FYI 64 Perf (Pixel
                # 2)", which is a child of this builder, uploads perf results,
                # and Pinpoint may trigger additional builds on this builder
                # during a bisect.
                perf_isolate_lookup=True,
            ),
        'Android FYI Release (Nexus 5)':
            bot_spec.BotSpec.create(
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
                bot_type=bot_spec.BUILDER_TESTER,
                testing={
                    'platform': 'linux',
                },
            ),
        'Android FYI Release (Nexus 5X)':
            bot_spec.BotSpec.create(
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
                bot_type=bot_spec.BUILDER_TESTER,
                testing={
                    'platform': 'linux',
                },
            ),
        'Android FYI Release (Nexus 6)':
            bot_spec.BotSpec.create(
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
                bot_type=bot_spec.BUILDER_TESTER,
                testing={
                    'platform': 'linux',
                },
            ),
        'Android FYI Release (Nexus 6P)':
            bot_spec.BotSpec.create(
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
                testing={
                    'platform': 'linux',
                },
            ),
        'Android FYI Release (Nexus 9)':
            bot_spec.BotSpec.create(
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
                testing={
                    'platform': 'linux',
                },
            ),
        'Android FYI Release (NVIDIA Shield TV)':
            bot_spec.BotSpec.create(
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
                testing={
                    'platform': 'linux',
                },
            ),
        'Android FYI Release (Pixel 2)':
            bot_spec.BotSpec.create(
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
                testing={
                    'platform': 'linux',
                },
            ),
        'Android FYI dEQP Release (Nexus 5X)':
            bot_spec.BotSpec.create(
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
                testing={
                    'platform': 'linux',
                },
            ),
        'Android FYI 32 Vk Release (Pixel 2)':
            bot_spec.BotSpec.create(
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
                testing={
                    'platform': 'linux',
                },
            ),
        'Android FYI 64 Vk Release (Pixel 2)':
            bot_spec.BotSpec.create(
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
                testing={
                    'platform': 'linux',
                },
            ),
        'Android FYI 32 dEQP Vk Release (Pixel 2)':
            bot_spec.BotSpec.create(
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
                testing={
                    'platform': 'linux',
                },
            ),
        'Android FYI 64 dEQP Vk Release (Pixel 2)':
            bot_spec.BotSpec.create(
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
                testing={
                    'platform': 'linux',
                },
            ),
        'Android FYI SkiaRenderer GL (Nexus 5X)':
            bot_spec.BotSpec.create(
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
                testing={
                    'platform': 'linux',
                },
            ),
        'Android FYI SkiaRenderer Vulkan (Pixel 2)':
            bot_spec.BotSpec.create(
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
                testing={
                    'platform': 'linux',
                },
            ),
        'Android FYI 64 Perf (Pixel 2)':
            bot_spec.BotSpec.create(
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
                testing={
                    'platform': 'linux',
                },
                serialize_tests=True,
            ),
        'GPU Fake Linux Builder':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'linux',
                },
            ),
        'Fake Linux Release (NVIDIA)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU Fake Linux Builder',
                testing={
                    'platform': 'linux',
                },
            ),
        'Linux FYI Ozone (Intel)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='GPU FYI Linux Ozone Builder',
                testing={
                    'platform': 'linux',
                },
                serialize_tests=True,
            ),

        # The following machines don't actually exist. They are specified
        # here only in order to allow the associated src-side JSON entries
        # to be read, and the "optional" GPU tryservers to be specified in
        # terms of them.
        'Optional Win10 x64 Release (NVIDIA)':
            bot_spec.BotSpec.create(bot_type=bot_spec.DUMMY_TESTER),
        'Optional Win10 x64 Release (Intel HD 630)':
            bot_spec.BotSpec.create(bot_type=bot_spec.DUMMY_TESTER),
        'Optional Linux Release (NVIDIA)':
            bot_spec.BotSpec.create(bot_type=bot_spec.DUMMY_TESTER),
        'Optional Linux Release (Intel HD 630)':
            bot_spec.BotSpec.create(bot_type=bot_spec.DUMMY_TESTER),
        'Optional Mac Release (Intel)':
            bot_spec.BotSpec.create(bot_type=bot_spec.DUMMY_TESTER),
        'Optional Mac Retina Release (NVIDIA)':
            bot_spec.BotSpec.create(bot_type=bot_spec.DUMMY_TESTER),
        'Optional Mac Retina Release (AMD)':
            bot_spec.BotSpec.create(bot_type=bot_spec.DUMMY_TESTER),
        'Optional Android Release (Nexus 5X)':
            bot_spec.BotSpec.create(
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
                testing={
                    'platform': 'linux',
                },
            ),

        # This following machines don't exist either; they are separate
        # configurations because we don't have the capacity to run all of
        # the tests on the GPU try servers. And to specify tests for
        # ANGLE's try servers separately from the gpu.fyi waterfall.
        'ANGLE GPU Android Release (Nexus 5X)':
            bot_spec.BotSpec.create(
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
                testing={
                    'platform': 'linux',
                },
            ),
        'ANGLE GPU Linux Release (NVIDIA)':
            bot_spec.BotSpec.create(bot_type=bot_spec.DUMMY_TESTER),
        'ANGLE GPU Linux Release (Intel HD 630)':
            bot_spec.BotSpec.create(bot_type=bot_spec.DUMMY_TESTER),
        'ANGLE GPU Mac Release (Intel)':
            bot_spec.BotSpec.create(bot_type=bot_spec.DUMMY_TESTER),
        'ANGLE GPU Mac Retina Release (NVIDIA)':
            bot_spec.BotSpec.create(bot_type=bot_spec.DUMMY_TESTER),
        'ANGLE GPU Mac Retina Release (AMD)':
            bot_spec.BotSpec.create(bot_type=bot_spec.DUMMY_TESTER),
        'ANGLE GPU Win10 x64 Release (NVIDIA)':
            bot_spec.BotSpec.create(bot_type=bot_spec.DUMMY_TESTER),
        'ANGLE GPU Win10 x64 Release (Intel HD 630)':
            bot_spec.BotSpec.create(bot_type=bot_spec.DUMMY_TESTER),
        'Win7 ANGLE Tryserver (AMD)':
            bot_spec.BotSpec.create(bot_type=bot_spec.DUMMY_TESTER),
    },
}
