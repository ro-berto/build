# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze

from RECIPE_MODULES.build.chromium_tests import try_spec


TRYBOTS = try_spec.TryDatabase.create({
    'tryserver.blink': {
        'linux-blink-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='linux-blink-rel-dummy',
            ),
        'linux-blink-optional-highdpi-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='linux-blink-optional-highdpi-rel-dummy',
            ),
        'mac10.12-blink-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='mac10.12-blink-rel-dummy',
            ),
        'mac10.13-blink-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='mac10.13-blink-rel-dummy',
            ),
        'mac10.14-blink-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='mac10.14-blink-rel-dummy',
            ),
        'mac10.15-blink-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='mac10.15-blink-rel-dummy',
            ),
        'mac11.0-blink-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='mac11.0-blink-rel-dummy',
            ),
        'win7-blink-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='win7-blink-rel-dummy',
            ),
        'win10-blink-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='win10-blink-rel-dummy',
            ),
    },
    'tryserver.chromium': {
        'android-official':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium',
                buildername='android-official',
            ),
        'fuchsia-official':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium',
                buildername='fuchsia-official',
            ),
        'linux-official':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium',
                buildername='linux-official',
            ),
        'mac-official':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium',
                buildername='mac-official',
            ),
        'win-official':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium',
                buildername='win-official',
            ),
        'win32-official':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium',
                buildername='win32-official',
            ),
    },
    'tryserver.chromium.android': {
        'android-10-arm64-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-10-arm64-rel',
            ),
        'android-asan':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.memory',
                buildername='android-asan',
            ),
        'android-bfcache-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-bfcache-rel',
            ),
        'android-cronet-arm-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-cronet-arm-dbg',
            ),
        'android-lollipop-arm-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-lollipop-arm-rel',
            ),
        'android-marshmallow-arm64-rel':
            try_spec.TrySpec.create([
                try_spec.TryMirror.create(
                    builder_group='chromium.android',
                    buildername='android-marshmallow-arm64-rel',
                ),
                try_spec.TryMirror.create(
                    builder_group='chromium.gpu',
                    buildername='Android Release (Nexus 5X)',
                ),
            ]),
        'android-marshmallow-x86-fyi-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android.fyi',
                buildername='android-marshmallow-x86-fyi-rel',
            ),
        'android-marshmallow-x86-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-marshmallow-x86-rel',
            ),
        'android-nougat-arm64-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-nougat-arm64-rel',
            ),
        'android-pie-arm64-coverage-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='android-code-coverage-native',
            ),
        'android-pie-arm64-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-pie-arm64-rel',
            ),
        'android-pie-x86-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-pie-x86-rel',
            ),
        'android_archive_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium',
                buildername='android-archive-rel',
            ),
        'android_arm64_dbg_recipe':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='Android arm64 Builder (dbg)',
                execution_mode=try_spec.COMPILE,
            ),
        'android_cfi_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.memory',
                buildername='Android CFI',
            ),
        'android_clang_dbg_recipe':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='Android ASAN (dbg)',
                execution_mode=try_spec.COMPILE,
            ),
        'android_compile_dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='Android arm Builder (dbg)',
                execution_mode=try_spec.COMPILE,
            ),
        'android_compile_x64_dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='Android x64 Builder (dbg)',
                execution_mode=try_spec.COMPILE,
            ),
        'android_compile_x86_dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='Android x86 Builder (dbg)',
                execution_mode=try_spec.COMPILE,
            ),
        'android_cronet':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-cronet-arm-rel',
                execution_mode=try_spec.COMPILE,
            ),
        'android_mojo':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='Mojo Android',
            ),
        'android_n5x_swarming_dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='Android arm64 Builder (dbg)',
                tester='Marshmallow 64 bit Tester',
            ),
        'android_optional_gpu_tests_rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Optional Android Release (Nexus 5X)',
            ),
        'android-webview-marshmallow-arm64-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='Android arm64 Builder (dbg)',
                tester='Android WebView M (dbg)',
            ),
        'android-webview-nougat-arm64-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='Android arm64 Builder (dbg)',
                tester='Android WebView N (dbg)',
            ),
        'android-webview-oreo-arm64-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='Android arm64 Builder (dbg)',
                tester='Android WebView O (dbg)',
            ),
        'android-webview-pie-arm64-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='Android arm64 Builder (dbg)',
                tester='Android WebView P (dbg)',
            ),
        'cast_shell_android':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='Cast Android (dbg)',
            ),
        'linux_android_dbg_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='Lollipop Phone Tester',
            ),
        'android_unswarmed_pixel_aosp':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='Android WebView N (dbg)',
            ),
        # Manually triggered GPU trybots.
        'gpu-fyi-try-android-l-nexus-5-32':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Android FYI Release (Nexus 5)',
            ),
        'gpu-fyi-try-android-m-nexus-5x-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Android FYI Release (Nexus 5X)',
            ),
        'gpu-fyi-try-android-m-nexus-5x-deqp-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Android FYI dEQP Release (Nexus 5X)',
            ),
        'gpu-fyi-try-android-m-nexus-5x-skgl-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Android FYI SkiaRenderer GL (Nexus 5X)',
            ),
        'gpu-fyi-try-android-l-nexus-6-32':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Android FYI Release (Nexus 6)',
            ),
        'gpu-fyi-try-android-m-nexus-6p-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Android FYI Release (Nexus 6P)',
            ),
        'gpu-fyi-try-android-m-nexus-9-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Android FYI Release (Nexus 9)',
            ),
        'gpu-fyi-try-android-n-nvidia-shield-tv-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Android FYI Release (NVIDIA Shield TV)',
            ),
        'gpu-fyi-try-android-p-pixel-2-32':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Android FYI Release (Pixel 2)',
            ),
        'gpu-fyi-try-android-p-pixel-2-skv-32':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Android FYI SkiaRenderer Vulkan (Pixel 2)',
            ),
        'gpu-fyi-try-android-q-pixel-2-deqp-vk-32':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Android FYI 32 dEQP Vk Release (Pixel 2)',
            ),
        'gpu-fyi-try-android-q-pixel-2-deqp-vk-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Android FYI 64 dEQP Vk Release (Pixel 2)',
            ),
        'gpu-fyi-try-android-q-pixel-2-vk-32':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Android FYI 32 Vk Release (Pixel 2)',
            ),
        'gpu-fyi-try-android-q-pixel-2-vk-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Android FYI 64 Vk Release (Pixel 2)',
            ),
        'gpu-try-android-m-nexus-5x-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu',
                buildername='Android Release (Nexus 5X)',
            ),
        'try-nougat-phone-tester':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='Android arm64 Builder (dbg)',
                tester='Nougat Phone Tester',
            ),
        'android-oreo-arm64-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='Android arm64 Builder (dbg)',
                tester='Oreo Phone Tester',
            ),
        'android-pie-arm64-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='Android arm64 Builder (dbg)',
                tester='android-pie-arm64-dbg',
            ),
        'android-pie-arm64-fyi-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android.fyi',
                buildername='android-pie-arm64-fyi-rel',
            ),
        'android-weblayer-pie-arm64-fyi-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android.fyi',
                buildername='Android WebLayer P FYI (rel)',
            ),
        'android-weblayer-pie-x86-fyi-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android.fyi',
                buildername='android-weblayer-pie-x86-fyi-rel',
            ),
        'android-webview-pie-arm64-fyi-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android.fyi',
                buildername='Android WebView P FYI (rel)',
            ),
    },
    'tryserver.chromium.angle': {
        'android_angle_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='ANGLE GPU Android Release (Nexus 5X)',
                retry_failed_shards=False,
            ),
        'android_angle_vk32_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Android FYI 32 Vk Release (Pixel 2)',
                retry_failed_shards=False,
            ),
        'android_angle_vk64_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Android FYI 64 Vk Release (Pixel 2)',
                retry_failed_shards=False,
            ),
        'android_angle_deqp_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Android FYI dEQP Release (Nexus 5X)',
                retry_failed_shards=False,
            ),
        'android_angle_vk32_deqp_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Android FYI 32 dEQP Vk Release (Pixel 2)',
                retry_failed_shards=False,
            ),
        'android_angle_vk64_deqp_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Android FYI 64 dEQP Vk Release (Pixel 2)',
                retry_failed_shards=False,
            ),
        'linux-angle-rel':
            try_spec.TrySpec.create(
                mirrors=[
                    try_spec.TryMirror.create(
                        builder_group='chromium.gpu.fyi',
                        buildername='GPU FYI Linux Builder',
                        tester='ANGLE GPU Linux Release (NVIDIA)',
                    ),
                    try_spec.TryMirror.create(
                        builder_group='chromium.gpu.fyi',
                        buildername='GPU FYI Linux Builder',
                        tester='ANGLE GPU Linux Release (Intel HD 630)',
                    ),
                ],
                retry_failed_shards=False,
            ),
        # TODO(fjhenigman): Add Ozone testers when possible.
        'linux_angle_ozone_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Linux Ozone Builder',
                execution_mode=try_spec.COMPILE,
            ),
        'linux_angle_deqp_rel_ng':
            try_spec.TrySpec.create(
                mirrors=[
                    try_spec.TryMirror.create(
                        builder_group='chromium.gpu.fyi',
                        buildername='GPU FYI Linux dEQP Builder',
                        tester='Linux FYI dEQP Release (NVIDIA)',
                    ),
                    try_spec.TryMirror.create(
                        builder_group='chromium.gpu.fyi',
                        buildername='GPU FYI Linux dEQP Builder',
                        tester='Linux FYI dEQP Release (Intel HD 630)',
                    ),
                ],
                retry_failed_shards=False,
            ),
        'mac-angle-rel':
            try_spec.TrySpec.create(
                mirrors=[
                    try_spec.TryMirror.create(
                        builder_group='chromium.gpu.fyi',
                        buildername='GPU FYI Mac Builder',
                        tester='ANGLE GPU Mac Release (Intel)',
                    ),
                    try_spec.TryMirror.create(
                        builder_group='chromium.gpu.fyi',
                        buildername='GPU FYI Mac Builder',
                        tester='ANGLE GPU Mac Retina Release (NVIDIA)',
                    ),
                    try_spec.TryMirror.create(
                        builder_group='chromium.gpu.fyi',
                        buildername='GPU FYI Mac Builder',
                        tester='ANGLE GPU Mac Retina Release (AMD)',
                    ),
                ],
                retry_failed_shards=False,
            ),
        'win-angle-rel-32':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Win Builder',
                tester='Win7 ANGLE Tryserver (AMD)',
                retry_failed_shards=False,
            ),
        'win-angle-rel-64':
            try_spec.TrySpec.create(
                mirrors=[
                    try_spec.TryMirror.create(
                        builder_group='chromium.gpu.fyi',
                        buildername='GPU FYI Win x64 Builder',
                        tester='ANGLE GPU Win10 x64 Release (NVIDIA)',
                    ),
                    try_spec.TryMirror.create(
                        builder_group='chromium.gpu.fyi',
                        buildername='GPU FYI Win x64 Builder',
                        tester='ANGLE GPU Win10 x64 Release (Intel HD 630)',
                    ),
                ],
                retry_failed_shards=False,
            ),
        'win-angle-deqp-rel-32':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Win dEQP Builder',
                tester='Win7 FYI dEQP Release (AMD)',
                retry_failed_shards=False,
            ),
        'win-angle-deqp-rel-64':
            try_spec.TrySpec.create(
                mirrors=[
                    try_spec.TryMirror.create(
                        builder_group='chromium.gpu.fyi',
                        buildername='GPU FYI Win x64 dEQP Builder',
                        tester='Win10 FYI x64 dEQP Release (NVIDIA)',
                    ),
                    try_spec.TryMirror.create(
                        builder_group='chromium.gpu.fyi',
                        buildername='GPU FYI Win x64 dEQP Builder',
                        tester='Win10 FYI x64 dEQP Release (Intel HD 630)',
                    ),
                ],
                retry_failed_shards=False,
            ),
        'fuchsia-angle-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Fuchsia Builder',
                execution_mode=try_spec.COMPILE,
            ),
    },
    'tryserver.chromium.linux': {
        'cast_shell_linux':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='Cast Linux',
            ),
        'cast_shell_audio_linux':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='Cast Audio Linux',
            ),
        'fuchsia_arm64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='Fuchsia ARM64',
            ),
        'fuchsia-arm64-cast':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='fuchsia-arm64-cast',
            ),
        'fuchsia_arm64_cast_audio':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='Fuchsia ARM64 Cast Audio',
            ),
        'fuchsia-compile-x64-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='fuchsia-x64-dbg',
                execution_mode=try_spec.COMPILE,
            ),
        'fuchsia-fyi-arm64-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='fuchsia-fyi-arm64-dbg',
            ),
        'fuchsia-fyi-arm64-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='fuchsia-fyi-arm64-rel',
            ),
        'fuchsia-fyi-x64-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='fuchsia-fyi-x64-dbg',
            ),
        'fuchsia-fyi-x64-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='fuchsia-fyi-x64-rel',
            ),
        'fuchsia_x64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='Fuchsia x64',
            ),
        'fuchsia-x64-cast':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='fuchsia-x64-cast',
            ),
        'fuchsia_x64_cast_audio':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='Fuchsia x64 Cast Audio',
            ),
        'linux-annotator-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='linux-annotator-rel',
            ),
        'linux-bfcache-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='linux-bfcache-rel',
            ),
        'linux-blink-heap-concurrent-marking-tsan-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='linux-blink-heap-concurrent-marking-tsan-rel',
            ),
        'linux-blink-heap-verification-try':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='linux-blink-heap-verification',
            ),
        # This trybot mirrors linux-rel
        'linux-dcheck-off-rel':
            try_spec.TrySpec.create([
                try_spec.TryMirror.create(
                    builder_group='chromium.linux',
                    buildername='Linux Builder',
                    tester='Linux Tests',
                ),
                try_spec.TryMirror.create(
                    builder_group='chromium.gpu',
                    buildername='GPU Linux Builder',
                    tester='Linux Release (NVIDIA)',
                ),
            ]),
        'linux-gcc-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='linux-gcc-rel',
            ),
        'linux-ozone-rel':
            try_spec.TrySpec.create([
                try_spec.TryMirror.create(
                    builder_group='chromium.linux',
                    buildername='linux-ozone-rel',
                    tester='Linux Ozone Tester (Headless)',
                ),
                try_spec.TryMirror.create(
                    builder_group='chromium.linux',
                    buildername='linux-ozone-rel',
                    tester='Linux Ozone Tester (X11)',
                ),
                try_spec.TryMirror.create(
                    builder_group='chromium.linux',
                    buildername='linux-ozone-rel',
                    tester='Linux Ozone Tester (Wayland)',
                ),
            ]),
        'linux-webkit-msan-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.memory',
                buildername='WebKit Linux MSAN',
            ),
        'linux_chromium_dbg_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='Linux Builder (dbg)',
                tester='Linux Tests (dbg)(1)',
            ),
        'linux-clang-tidy-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='Linux Builder (dbg)',
                execution_mode=try_spec.COMPILE,
            ),
        'linux-clang-tidy-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='Linux Builder',
                execution_mode=try_spec.COMPILE,
            ),
        'linux-rel':
            try_spec.TrySpec.create(
                mirrors=[
                    try_spec.TryMirror.create(
                        builder_group='chromium.linux',
                        buildername='Linux Builder',
                        tester='Linux Tests',
                    ),
                    try_spec.TryMirror.create(
                        builder_group='chromium.gpu',
                        buildername='GPU Linux Builder',
                        tester='Linux Release (NVIDIA)',
                    ),
                ],
                analyze_deps_autorolls=True,
            ),
        'linux_chromium_asan_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.memory',
                buildername='Linux ASan LSan Builder',
                tester='Linux ASan LSan Tests (1)',
            ),
        'linux_chromium_compile_dbg_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='Linux Builder (dbg)',
                execution_mode=try_spec.COMPILE,
            ),
        'linux_chromium_compile_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='Linux Builder',
                execution_mode=try_spec.COMPILE,
            ),
        'linux_chromium_archive_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium',
                buildername='linux-archive-rel',
            ),
        'linux_chromium_clobber_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium',
                buildername='linux-archive-rel',
                execution_mode=try_spec.COMPILE,
            ),
        'linux_chromium_chromeos_asan_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.memory',
                buildername='Linux Chromium OS ASan LSan Builder',
                tester='Linux Chromium OS ASan LSan Tests (1)',
            ),
        'linux_chromium_chromeos_msan_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.memory',
                buildername='Linux ChromiumOS MSan Builder',
                tester='Linux ChromiumOS MSan Tests',
            ),
        'linux_chromium_compile_dbg_32_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='Linux Builder (dbg)(32)',
                execution_mode=try_spec.COMPILE,
            ),
        'linux_chromium_msan_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.memory',
                buildername='Linux MSan Builder',
                tester='Linux MSan Tests',
            ),
        'linux_chromium_tsan_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.memory',
                buildername='Linux TSan Builder',
                tester='Linux TSan Tests',
            ),
        'linux_chromium_cfi_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.memory',
                buildername='Linux CFI',
            ),
        'linux_chromium_ubsan_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.clang',
                buildername='UBSanVptr Linux',
            ),
        'linux_layout_tests_composite_after_paint':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='WebKit Linux composite_after_paint Dummy Builder',
            ),
        'linux_layout_tests_layout_ng_disabled':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='WebKit Linux layout_ng_disabled Builder',
            ),
        'linux_mojo':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='Mojo Linux',
            ),
        'linux_mojo_chromeos':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='Mojo ChromiumOS',
            ),
        'linux-perfetto-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='linux-perfetto-rel',
            ),
        'linux-viz-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='Linux Viz',
            ),
        'linux_vr':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='VR Linux',
            ),
        'leak_detection_linux':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='Leak Detection Linux',
            ),
        'layout_test_leak_detection':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.memory',
                buildername='WebKit Linux Leak',
            ),
        # Optional GPU bots.
        'linux_optional_gpu_tests_rel':
            try_spec.TrySpec.create([
                try_spec.TryMirror.create(
                    builder_group='chromium.gpu.fyi',
                    buildername='GPU FYI Linux Builder DEPS ANGLE',
                    tester='Optional Linux Release (NVIDIA)',
                ),
                try_spec.TryMirror.create(
                    builder_group='chromium.gpu.fyi',
                    buildername='GPU FYI Linux Builder DEPS ANGLE',
                    tester='Optional Linux Release (Intel HD 630)',
                ),
            ]),
        # Manually triggered GPU trybots.
        'gpu-fyi-try-linux-intel-dqp':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Linux dEQP Builder',
                tester='Linux FYI dEQP Release (Intel HD 630)',
            ),
        'gpu-fyi-try-linux-intel-exp':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Linux Builder',
                tester='Linux FYI Experimental Release (Intel HD 630)',
            ),
        'gpu-fyi-try-linux-intel-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Linux Builder',
                tester='Linux FYI Release (Intel HD 630)',
            ),
        'gpu-fyi-try-linux-intel-sk-dawn-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername=\
                'Linux FYI SkiaRenderer Dawn Release (Intel HD 630)',
            ),
        'gpu-fyi-try-linux-intel-skv':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Linux Builder',
                tester='Linux FYI SkiaRenderer Vulkan (Intel HD 630)',
            ),
        'gpu-fyi-try-linux-nvidia-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Linux Builder (dbg)',
                tester='Linux FYI Debug (NVIDIA)',
            ),
        'gpu-fyi-try-linux-nvidia-dqp':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Linux dEQP Builder',
                tester='Linux FYI dEQP Release (NVIDIA)',
            ),
        'gpu-fyi-try-linux-nvidia-exp':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Linux Builder',
                tester='Linux FYI Experimental Release (NVIDIA)',
            ),
        'gpu-fyi-try-linux-nvidia-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Linux Builder',
                tester='Linux FYI Release (NVIDIA)',
            ),
        'gpu-fyi-try-linux-nvidia-skv':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Linux Builder',
                tester='Linux FYI SkiaRenderer Vulkan (NVIDIA)',
            ),
        'gpu-fyi-try-linux-nvidia-tsn':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Linux FYI GPU TSAN Release',
            ),
        'gpu-try-linux-nvidia-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu',
                buildername='GPU Linux Builder (dbg)',
                tester='Linux Debug (NVIDIA)',
            ),
        'gpu-try-linux-nvidia-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu',
                buildername='GPU Linux Builder',
                tester='Linux Release (NVIDIA)',
            ),
        'linux-lacros-fyi-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='linux-lacros-builder-fyi-rel',
                tester='linux-lacros-tester-fyi-rel',
            ),
        'linux-trusty-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='linux-trusty-rel',
            ),
        'linux-wpt-fyi-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='linux-wpt-fyi-rel',
            ),
        'network_service_linux':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='Network Service Linux',
            ),
    },
    'tryserver.chromium.chromiumos': {
        'chromeos-amd64-generic-cfi-thin-lto-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.chromiumos',
                buildername='chromeos-amd64-generic-cfi-thin-lto-rel',
            ),
        'chromeos-amd64-generic-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.chromiumos',
                buildername='chromeos-amd64-generic-dbg',
            ),
        'chromeos-amd64-generic-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.chromiumos',
                buildername='chromeos-amd64-generic-rel',
            ),
        'chromeos-arm-generic-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.chromiumos',
                buildername='chromeos-arm-generic-dbg',
            ),
        'chromeos-arm-generic-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.chromiumos',
                buildername='chromeos-arm-generic-rel',
            ),
        'chromeos-kevin-compile-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.chromiumos',
                buildername='chromeos-kevin-rel',
                execution_mode=try_spec.COMPILE,
            ),
        'chromeos-kevin-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.chromiumos',
                buildername='chromeos-kevin-rel',
            ),
        'linux-chromeos-compile-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.chromiumos',
                buildername='linux-chromeos-dbg',
                execution_mode=try_spec.COMPILE,
            ),
        'linux-chromeos-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.chromiumos',
                buildername='linux-chromeos-dbg',
            ),
        'linux-chromeos-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.chromiumos',
                buildername='linux-chromeos-rel',
            ),
       'linux-lacros-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.chromiumos',
                buildername='linux-lacros-rel',
            ),
        # Manually triggered GPU trybots.
        'gpu-fyi-try-chromeos-amd64-generic':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='ChromeOS FYI Release (amd64-generic)',
            ),
        'gpu-fyi-try-chromeos-kevin':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='ChromeOS FYI Release (kevin)',
            ),
    },
    'tryserver.chromium.mac': {
        'ios-device':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.mac',
                buildername='ios-device',
            ),
        'ios-simulator-code-coverage':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='ios-simulator-code-coverage',
            ),
        'ios-simulator-cronet':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='ios-simulator-cronet',
            ),
        'ios-simulator-full-configs':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.mac',
                buildername='ios-simulator-full-configs',
            ),
        'ios-simulator-multi-window':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='ios-simulator-multi-window',
            ),
        'ios-simulator-noncq':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.mac',
                buildername='ios-simulator-noncq',
            ),
        'ios-simulator':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.mac',
                buildername='ios-simulator',
            ),
        'ios13-beta-simulator':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='ios13-beta-simulator',
            ),
        'ios13-sdk-simulator':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='ios13-sdk-simulator',
            ),
        'ios14-beta-simulator':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='ios14-beta-simulator',
            ),
        'ios14-sdk-simulator':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='ios14-sdk-simulator',
            ),
        'mac_chromium_archive_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium',
                buildername='mac-archive-rel',
            ),
        'mac_chromium_dbg_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.mac',
                buildername='Mac Builder (dbg)',
                tester='Mac10.13 Tests (dbg)',
            ),
        'mac-osxbeta-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.mac',
                buildername='Mac Builder',
                tester_group='chromium.fyi',
                tester='mac-osxbeta-rel',
            ),
        'mac-arm64-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.mac',
                buildername='mac-arm64-rel',
            ),
        'mac-coverage-rel':
            try_spec.TrySpec.create([
                try_spec.TryMirror.create(
                    builder_group='chromium.mac',
                    buildername='Mac Builder Code Coverage',
                    tester='Mac10.13 Tests Code Coverage',
                ),
                try_spec.TryMirror.create(
                    builder_group='chromium.gpu',
                    buildername='GPU Mac Builder Code Coverage',
                    tester='Mac Release (Intel) Code Coverage',
                ),
                try_spec.TryMirror.create(
                    builder_group='chromium.gpu',
                    buildername='GPU Mac Builder Code Coverage',
                    tester='Mac Retina Release (AMD) Code Coverage',
                ),
            ]),
        'mac-rel':
            try_spec.TrySpec.create([
                try_spec.TryMirror.create(
                    builder_group='chromium.mac',
                    buildername='Mac Builder',
                    tester='Mac10.13 Tests',
                ),
                try_spec.TryMirror.create(
                    builder_group='chromium.gpu',
                    buildername='GPU Mac Builder',
                    tester='Mac Release (Intel)',
                ),
                try_spec.TryMirror.create(
                    builder_group='chromium.gpu',
                    buildername='GPU Mac Builder',
                    tester='Mac Retina Release (AMD)',
                ),
            ]),
        'mac_chromium_10.10':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.mac',
                buildername='Mac Builder',
                tester='Mac10.10 Tests',
            ),
        'mac_chromium_10.12_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.mac',
                buildername='Mac Builder',
                tester='Mac10.12 Tests',
            ),
        'mac_chromium_10.13_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.mac',
                buildername='Mac Builder',
                tester='Mac10.13 Tests',
            ),
        'mac_chromium_10.14_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.mac',
                buildername='Mac Builder',
                tester='Mac10.14 Tests',
            ),
        'mac_chromium_10.15_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.mac',
                buildername='Mac Builder',
                tester='Mac10.15 Tests',
            ),
        'mac_chromium_11.0_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='Mac Builder Next',
                tester='Mac11.0 Tests',
            ),
        'mac_chromium_compile_dbg_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.mac',
                buildername='Mac Builder (dbg)',
                execution_mode=try_spec.COMPILE,
            ),
        'mac_chromium_compile_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.mac',
                buildername='Mac Builder',
                execution_mode=try_spec.COMPILE,
            ),
        'mac_chromium_asan_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.memory',
                buildername='Mac ASan 64 Builder',
                tester='Mac ASan 64 Tests (1)',
            ),
        # Optional GPU bots.
        'mac_optional_gpu_tests_rel':
            try_spec.TrySpec.create([
                try_spec.TryMirror.create(
                    builder_group='chromium.gpu.fyi',
                    buildername='GPU FYI Mac Builder DEPS ANGLE',
                    tester='Optional Mac Release (Intel)',
                ),
                try_spec.TryMirror.create(
                    builder_group='chromium.gpu.fyi',
                    buildername='GPU FYI Mac Builder DEPS ANGLE',
                    tester='Optional Mac Retina Release (NVIDIA)',
                ),
                try_spec.TryMirror.create(
                    builder_group='chromium.gpu.fyi',
                    buildername='GPU FYI Mac Builder DEPS ANGLE',
                    tester='Optional Mac Retina Release (AMD)',
                ),
            ]),
        # Manually triggered GPU trybots.
        'gpu-fyi-try-mac-amd-dqp':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Mac dEQP Builder',
                tester='Mac FYI dEQP Release AMD',
            ),
        'gpu-fyi-try-mac-amd-pro-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Mac Builder',
                tester='Mac Pro FYI Release (AMD)',
            ),
        'gpu-fyi-try-mac-amd-retina-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Mac Builder (dbg)',
                tester='Mac FYI Retina Debug (AMD)',
            ),
        'gpu-fyi-try-mac-amd-retina-exp':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Mac Builder',
                tester='Mac FYI Experimental Retina Release (AMD)',
            ),
        'gpu-fyi-try-mac-amd-retina-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Mac Builder',
                tester='Mac FYI Retina Release (AMD)',
            ),
        'gpu-fyi-try-mac-arm64-apple-dtk-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Mac FYI arm64 Release (Apple DTK)',
            ),
        'gpu-fyi-try-mac-asan':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Mac FYI GPU ASAN Release',
            ),
        'gpu-fyi-try-mac-intel-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Mac Builder (dbg)',
                tester='Mac FYI Debug (Intel)',
            ),
        'gpu-fyi-try-mac-intel-dqp':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Mac dEQP Builder',
                tester='Mac FYI dEQP Release Intel',
            ),
        'gpu-fyi-try-mac-intel-exp':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Mac Builder',
                tester='Mac FYI Experimental Release (Intel)',
            ),
        'gpu-fyi-try-mac-intel-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Mac Builder',
                tester='Mac FYI Release (Intel)',
            ),
        'gpu-fyi-try-mac-nvidia-retina-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Mac Builder (dbg)',
                tester='Mac FYI Retina Debug (NVIDIA)',
            ),
        'gpu-fyi-try-mac-nvidia-retina-exp':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Mac Builder',
                tester='Mac FYI Experimental Retina Release (NVIDIA)',
            ),
        'gpu-fyi-try-mac-nvidia-retina-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Mac Builder',
                tester='Mac FYI Retina Release (NVIDIA)',
            ),
        'gpu-try-mac-amd-retina-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu',
                buildername='GPU Mac Builder (dbg)',
                tester='Mac Retina Debug (AMD)',
            ),
        'gpu-try-mac-intel-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu',
                buildername='GPU Mac Builder (dbg)',
                tester='Mac Debug (Intel)',
            ),
    },
    'tryserver.chromium.perf': {
        'Android Compile Perf':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.perf',
                buildername='android-builder-perf',
            ),
        'Android arm64 Compile Perf':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.perf',
                buildername='android_arm64-builder-perf',
            ),
        'Linux Builder Perf':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.perf',
                buildername='linux-builder-perf',
            ),
        'Mac Builder Perf':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.perf',
                buildername='mac-builder-perf',
            ),
        'Win Builder Perf':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.perf',
                buildername='win32-builder-perf',
            ),
        'Win x64 Builder Perf':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.perf',
                buildername='win64-builder-perf',
            ),
    },
    'tryserver.chromium.win': {
        'win-asan':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.memory',
                buildername='win-asan',
            ),
        'win-annotator-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='win-annotator-rel',
            ),
        'win_archive':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium',
                buildername='win32-archive-rel',
            ),
        'win_x64_archive':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium',
                buildername='win-archive-rel',
            ),
        'win_chromium_dbg_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.win',
                buildername='Win Builder (dbg)',
                tester='Win7 Tests (dbg)(1)',
            ),
        'win7-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.win',
                buildername='Win Builder',
                tester='Win7 Tests (1)',
            ),
        'win10_chromium_x64_dbg_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.win',
                buildername='Win x64 Builder (dbg)',
                tester='Win10 Tests x64 (dbg)',
            ),
        'win10_chromium_x64_rel_ng':
            try_spec.TrySpec.create([
                try_spec.TryMirror.create(
                    builder_group='chromium.win',
                    buildername='Win x64 Builder',
                    tester='Win10 Tests x64',
                ),
                try_spec.TryMirror.create(
                    builder_group='chromium.gpu',
                    buildername='GPU Win x64 Builder',
                    tester='Win10 x64 Release (NVIDIA)',
                ),
            ]),
        'win_chromium_compile_dbg_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.win',
                buildername='Win Builder (dbg)',
                execution_mode=try_spec.COMPILE,
            ),
        'win_chromium_compile_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.win',
                buildername='Win Builder',
                execution_mode=try_spec.COMPILE,
            ),
        'win_chromium_x64_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.win',
                buildername='Win x64 Builder',
                tester='Win 7 Tests x64 (1)',
            ),
        'win_mojo':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='Mojo Windows',
            ),
        # Optional GPU bots.
        # This trybot used to mirror "Optional Win7 Release (AMD)",
        # but that had to be disabled due to capacity constraints.
        'win_optional_gpu_tests_rel':
            try_spec.TrySpec.create([
                try_spec.TryMirror.create(
                    builder_group='chromium.gpu.fyi',
                    buildername='GPU FYI Win x64 Builder DEPS ANGLE',
                    tester='Optional Win10 x64 Release (NVIDIA)',
                ),
                try_spec.TryMirror.create(
                    builder_group='chromium.gpu.fyi',
                    buildername='GPU FYI Win x64 Builder DEPS ANGLE',
                    tester='Optional Win10 x64 Release (Intel HD 630)',
                ),
            ]),
        # Manually triggered GPU trybots.
        'gpu-fyi-try-win7-amd-dbg-32':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Win Builder (dbg)',
                tester='Win7 FYI Debug (AMD)',
            ),
        'gpu-fyi-try-win7-amd-dqp-32':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Win dEQP Builder',
                tester='Win7 FYI dEQP Release (AMD)',
            ),
        'gpu-fyi-try-win7-amd-rel-32':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Win Builder',
                tester='Win7 FYI Release (AMD)',
            ),
        'gpu-fyi-try-win7-nvidia-dqp-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Win x64 dEQP Builder',
                tester='Win7 FYI x64 dEQP Release (NVIDIA)',
            ),
        'gpu-fyi-try-win7-nvidia-rel-32':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Win Builder',
                tester='Win7 FYI Release (NVIDIA)',
            ),
        'gpu-fyi-try-win7-nvidia-rel-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Win x64 Builder',
                tester='Win7 FYI x64 Release (NVIDIA)',
            ),
        'gpu-fyi-try-win10-intel-dqp-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Win x64 dEQP Builder',
                tester='Win10 FYI x64 dEQP Release (Intel HD 630)',
            ),
        'gpu-fyi-try-win10-intel-exp-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Win x64 Builder',
                tester='Win10 FYI x64 Exp Release (Intel HD 630)',
            ),
        'gpu-fyi-try-win10-intel-rel-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Win x64 Builder',
                tester='Win10 FYI x64 Release (Intel HD 630)',
            ),
        'gpu-fyi-try-win10-nvidia-dbg-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Win x64 Builder (dbg)',
                tester='Win10 FYI x64 Debug (NVIDIA)',
            ),
        'gpu-fyi-try-win10-nvidia-dqp-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Win x64 dEQP Builder',
                tester='Win10 FYI x64 dEQP Release (NVIDIA)',
            ),
        'gpu-fyi-try-win10-nvidia-dx12vk-dbg-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Win x64 DX12 Vulkan Builder (dbg)',
                tester='Win10 FYI x64 DX12 Vulkan Debug (NVIDIA)',
            ),
        'gpu-fyi-try-win10-nvidia-dx12vk-rel-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Win x64 DX12 Vulkan Builder',
                tester='Win10 FYI x64 DX12 Vulkan Release (NVIDIA)',
            ),
        'gpu-fyi-try-win10-nvidia-exp-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Win x64 Builder',
                tester='Win10 FYI x64 Exp Release (NVIDIA)',
            ),
        'gpu-fyi-try-win10-nvidia-rel-32':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Win Builder',
                tester='Win10 FYI x86 Release (NVIDIA)',
            ),
        'gpu-fyi-try-win10-nvidia-rel-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Win x64 Builder',
                tester='Win10 FYI x64 Release (NVIDIA)',
            ),
        'gpu-fyi-try-win10-nvidia-sk-dawn-rel-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Win10 FYI x64 SkiaRenderer Dawn Release (NVIDIA)',
            ),
        'gpu-fyi-try-win10-nvidia-skgl-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Win x64 Builder',
                tester='Win10 FYI x64 SkiaRenderer GL (NVIDIA)',
            ),
    },
    # Dawn GPU bots
    'tryserver.chromium.dawn': {
        'dawn-linux-x64-deps-rel':
            try_spec.TrySpec.create([
                try_spec.TryMirror.create(
                    builder_group='chromium.dawn',
                    buildername='Dawn Linux x64 DEPS Builder',
                    tester='Dawn Linux x64 DEPS Release (Intel HD 630)',
                ),
                try_spec.TryMirror.create(
                    builder_group='chromium.dawn',
                    buildername='Dawn Linux x64 DEPS Builder',
                    tester='Dawn Linux x64 DEPS Release (NVIDIA)',
                ),
            ]),
        'dawn-mac-x64-deps-rel':
            try_spec.TrySpec.create([
                try_spec.TryMirror.create(
                    builder_group='chromium.dawn',
                    buildername='Dawn Mac x64 DEPS Builder',
                    tester='Dawn Mac x64 DEPS Release (AMD)',
                ),
                try_spec.TryMirror.create(
                    builder_group='chromium.dawn',
                    buildername='Dawn Mac x64 DEPS Builder',
                    tester='Dawn Mac x64 DEPS Release (Intel)',
                ),
            ]),
        'dawn-win10-x86-deps-rel':
            try_spec.TrySpec.create([
                try_spec.TryMirror.create(
                    builder_group='chromium.dawn',
                    buildername='Dawn Win10 x86 DEPS Builder',
                    tester='Dawn Win10 x86 DEPS Release (Intel HD 630)',
                ),
                try_spec.TryMirror.create(
                    builder_group='chromium.dawn',
                    buildername='Dawn Win10 x86 DEPS Builder',
                    tester='Dawn Win10 x86 DEPS Release (NVIDIA)',
                ),
            ]),
        'dawn-win10-x64-deps-rel':
            try_spec.TrySpec.create([
                try_spec.TryMirror.create(
                    builder_group='chromium.dawn',
                    buildername='Dawn Win10 x64 DEPS Builder',
                    tester='Dawn Win10 x64 DEPS Release (Intel HD 630)',
                ),
                try_spec.TryMirror.create(
                    builder_group='chromium.dawn',
                    buildername='Dawn Win10 x64 DEPS Builder',
                    tester='Dawn Win10 x64 DEPS Release (NVIDIA)',
                ),
            ]),
        'linux-dawn-rel':
            try_spec.TrySpec.create([
                try_spec.TryMirror.create(
                    builder_group='chromium.dawn',
                    buildername='Dawn Linux x64 Builder',
                    tester='Dawn Linux x64 Release (Intel HD 630)',
                ),
                try_spec.TryMirror.create(
                    builder_group='chromium.dawn',
                    buildername='Dawn Linux x64 Builder',
                    tester='Dawn Linux x64 Release (NVIDIA)',
                ),
            ]),
        'mac-dawn-rel':
            try_spec.TrySpec.create([
                try_spec.TryMirror.create(
                    builder_group='chromium.dawn',
                    buildername='Dawn Mac x64 Builder',
                    tester='Dawn Mac x64 Release (AMD)',
                ),
                try_spec.TryMirror.create(
                    builder_group='chromium.dawn',
                    buildername='Dawn Mac x64 Builder',
                    tester='Dawn Mac x64 Release (Intel)',
                ),
            ]),
        'win-dawn-rel':
            try_spec.TrySpec.create([
                try_spec.TryMirror.create(
                    builder_group='chromium.dawn',
                    buildername='Dawn Win10 x64 Builder',
                    tester='Dawn Win10 x64 Release (Intel HD 630)',
                ),
                try_spec.TryMirror.create(
                    builder_group='chromium.dawn',
                    buildername='Dawn Win10 x64 Builder',
                    tester='Dawn Win10 x64 Release (NVIDIA)',
                ),
            ]),

        # Manually triggered Dawn trybots.
        'dawn-try-win10-x86-rel':
            try_spec.TrySpec.create([
                try_spec.TryMirror.create(
                    builder_group='chromium.dawn',
                    buildername='Dawn Win10 x86 Builder',
                    tester='Dawn Win10 x86 Release (Intel HD 630)',
                ),
                try_spec.TryMirror.create(
                    builder_group='chromium.dawn',
                    buildername='Dawn Win10 x86 Builder',
                    tester='Dawn Win10 x86 Release (NVIDIA)',
                ),
            ]),
        'dawn-try-win10-x64-asan-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.dawn',
                buildername='Dawn Win10 x64 ASAN Release',
            ),
    },
    # SWANGLE bots
    'tryserver.chromium.swangle': {
        'linux-swangle-chromium-try-x64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='linux-swangle-chromium-x64',
            ),
        'linux-swangle-try-tot-angle-x64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='linux-swangle-tot-angle-x64',
            ),
        'linux-swangle-try-tot-angle-x86':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='linux-swangle-tot-angle-x86',
            ),
        'linux-swangle-try-tot-swiftshader-x64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='linux-swangle-tot-swiftshader-x64',
            ),
        'linux-swangle-try-tot-swiftshader-x86':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='linux-swangle-tot-swiftshader-x86',
            ),
        'linux-swangle-try-x64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='linux-swangle-x64',
            ),
        'linux-swangle-try-x86':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='linux-swangle-x86',
            ),
        'mac-swangle-chromium-try-x64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='mac-swangle-chromium-x64',
            ),
        'win-swangle-chromium-try-x86':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='win-swangle-chromium-x86',
            ),
        'win-swangle-try-tot-angle-x64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='win-swangle-tot-angle-x64',
            ),
        'win-swangle-try-tot-angle-x86':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='win-swangle-tot-angle-x86',
            ),
        'win-swangle-try-tot-swiftshader-x64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='win-swangle-tot-swiftshader-x64',
            ),
        'win-swangle-try-tot-swiftshader-x86':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='win-swangle-tot-swiftshader-x86',
            ),
        'win-swangle-try-x64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='win-swangle-x64',
            ),
        'win-swangle-try-x86':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='win-swangle-x86',
            ),
    },
    'tryserver.v8': {
        'v8_linux_blink_rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='linux-blink-rel-dummy',
            ),
        'v8_linux_chromium_gn_rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='client.v8.fyi',
                buildername='V8 Linux GN',
            ),
    },
    'tryserver.webrtc': {
        'win_chromium_compile':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='tryserver.webrtc',
                buildername='win_chromium_compile',
                execution_mode=try_spec.COMPILE,
            ),
        'win_chromium_compile_dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='tryserver.webrtc',
                buildername='win_chromium_compile_dbg',
                execution_mode=try_spec.COMPILE,
            ),
        'mac_chromium_compile':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='tryserver.webrtc',
                buildername='mac_chromium_compile',
                execution_mode=try_spec.COMPILE,
            ),
        'linux_chromium_compile':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='tryserver.webrtc',
                buildername='linux_chromium_compile',
                execution_mode=try_spec.COMPILE,
            ),
        'linux_chromium_compile_dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='tryserver.webrtc',
                buildername='linux_chromium_compile_dbg',
                execution_mode=try_spec.COMPILE,
            ),
        'android_chromium_compile':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='tryserver.webrtc',
                buildername='android_chromium_compile',
                execution_mode=try_spec.COMPILE,
            ),
    },
})
