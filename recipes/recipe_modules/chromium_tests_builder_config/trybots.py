# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import try_spec

TRYBOTS = try_spec.TryDatabase.create({
    # The config for the following builders is now specified src-side in
    # //infra/config/subprojects/chromium/try/tryserver.blink.star
    # * android-oreo-arm64-dbg
    # * android-webview-marshmallow-arm64-dbg
    # * android-webview-nougat-arm64-dbg
    # * android-webview-oreo-arm64-dbg
    # * android-webview-pie-arm64-dbg
    # * android_arm64_dbg_recipe
    # * android_n5x_swarming_dbg
    # * android_unswarmed_pixel_aosp
    # * linux-blink-rel
    # * try-nougat-phone-tester
    'tryserver.blink': {
        'linux-blink-optional-highdpi-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='linux-blink-optional-highdpi-rel-dummy',
                retry_failed_shards=False,
            ),
        'mac10.12-blink-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='mac10.12-blink-rel-dummy',
                retry_failed_shards=False,
            ),
        'mac10.13-blink-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='mac10.13-blink-rel-dummy',
                retry_failed_shards=False,
            ),
        'mac10.14-blink-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='mac10.14-blink-rel-dummy',
                retry_failed_shards=False,
            ),
        'mac10.15-blink-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='mac10.15-blink-rel-dummy',
                retry_failed_shards=False,
            ),
        'mac11.0-blink-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='mac11.0-blink-rel-dummy',
                retry_failed_shards=False,
            ),
        'mac11.0.arm64-blink-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='mac11.0.arm64-blink-rel-dummy',
                retry_failed_shards=False,
            ),
        'win7-blink-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='win7-blink-rel-dummy',
                retry_failed_shards=False,
            ),
        'win10.20h2-blink-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='win10.20h2-blink-rel-dummy',
                retry_failed_shards=False,
            ),
        'win11-blink-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='win11-blink-rel-dummy',
                retry_failed_shards=False,
            ),
    },
    # The config for the following builders is now specified src-side in
    # //infra/config/subprojects/chromium/try/tryserver.chromium.star
    # * win-official
    # * win32-official
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
    },
    # The config for the following builders is now specified src-side in
    # //infra/config/subprojects/chromium/try/tryserver.chromium.android.star
    # * android_archive_rel_ng
    # * android_compile_dbg
    # * android_compile_x64_dbg
    # * android-12-x64-dbg
    # * android-inverse-fieldtrials-pie-x86-fyi-rel
    # * android-pie-x86-rel
    # * android-weblayer-pie-x86-rel-tests
    # * android-webview-12-x64-dbg
    'tryserver.chromium.android': {
        'android-10-arm64-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-10-arm64-rel',
            ),
        'android-11-x86-fyi-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android.fyi',
                buildername='android-11-x86-fyi-rel',
            ),
        'android-11-x86-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-11-x86-rel',
            ),
        # TODO(crbug.com/1225851): Remote FYI config after
        # android-12-x64-rel is  up and running.
        'android-12-x64-fyi-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android.fyi',
                buildername='android-12-x64-fyi-rel',
            ),
        'android-12-x64-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-12-x64-rel',
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
        'android-cronet-arm64-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-cronet-arm64-dbg',
            ),
        'android-cronet-arm64-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-cronet-arm64-rel',
            ),
        'android-cronet-asan-arm-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-cronet-asan-arm-rel',
            ),
        'android-cronet-x86-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-cronet-x86-dbg',
            ),
        'android-cronet-x86-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-cronet-x86-rel',
            ),
        'android-cronet-x86-dbg-10-tests':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-cronet-x86-dbg',
                tester='android-cronet-x86-dbg-10-tests',
            ),
        'android-cronet-x86-dbg-11-tests':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-cronet-x86-dbg',
                tester='android-cronet-x86-dbg-11-tests',
            ),
        'android-cronet-x86-dbg-oreo-tests':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-cronet-x86-dbg',
                tester='android-cronet-x86-dbg-oreo-tests',
            ),
        'android-cronet-x86-dbg-pie-tests':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-cronet-x86-dbg',
                tester='android-cronet-x86-dbg-pie-tests',
            ),
        'android-cronet-x86-rel-kitkat-tests':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-cronet-x86-rel',
                tester='android-cronet-x86-rel-kitkat-tests',
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
            ],),
        'android-marshmallow-x86-fyi-rel-reviver':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android.fyi',
                buildername='android-marshmallow-x86-fyi-rel-reviver',
            ),
        'android-marshmallow-x86-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-marshmallow-x86-rel',
                regression_test_selection=try_spec.QUICK_RUN_ONLY,
            ),
        'android-marshmallow-x86-rel-non-cq':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-marshmallow-x86-rel-non-cq',
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
        'android-pie-arm64-coverage-experimental-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-pie-arm64-coverage-experimental-rel',
            ),
        'android-pie-arm64-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-pie-arm64-rel',
                regression_test_selection=try_spec.QUICK_RUN_ONLY,
            ),
        'android-pie-arm64-wpt-rel-non-cq':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android.fyi',
                buildername='android-pie-arm64-wpt-rel-non-cq',
            ),
        'android-chrome-pie-x86-wpt-fyi-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android.fyi',
                buildername='android-chrome-pie-x86-wpt-fyi-rel',
            ),
        'android-weblayer-10-x86-rel-tests':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-weblayer-with-aosp-webview-x86-rel',
                tester='android-weblayer-10-x86-rel-tests',
            ),
        'android-weblayer-11-x86-rel-tests':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android.fyi',
                buildername='android-weblayer-with-aosp-webview-x86-fyi-rel',
                tester='android-weblayer-11-x86-rel-tests',
            ),
        'android-weblayer-marshmallow-x86-rel-tests':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-weblayer-with-aosp-webview-x86-rel',
                tester='android-weblayer-marshmallow-x86-rel-tests',
            ),
        'android-weblayer-pie-x86-wpt-fyi-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android.fyi',
                buildername='android-weblayer-pie-x86-wpt-fyi-rel',
            ),
        'android-weblayer-pie-x86-wpt-smoketest':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android.fyi',
                buildername='android-weblayer-pie-x86-wpt-smoketest',
            ),
        'android-webview-pie-x86-wpt-fyi-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android.fyi',
                buildername='android-webview-pie-x86-wpt-fyi-rel',
            ),
        'android_compile_x86_dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='Android x86 Builder (dbg)',
                is_compile_only=True,
                include_all_triggered_testers=True,
            ),
        'android_cronet':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-cronet-arm-rel',
                is_compile_only=True,
            ),
        'android_optional_gpu_tests_rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='Optional Android Release (Pixel 4)',
                retry_failed_shards=False,
            ),
        'cast_shell_android':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='Cast Android (dbg)',
            ),
        # Manually triggered GPU trybots.
        'gpu-fyi-try-android-l-nexus-5-32':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Android arm Builder',
                tester='Android FYI Release (Nexus 5)',
            ),
        'gpu-fyi-try-android-m-nexus-5x-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Android arm64 Builder',
                tester='Android FYI Release (Nexus 5X)',
            ),
        'gpu-fyi-try-android-nvidia-shield-tv':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Android arm Builder',
                tester='Android FYI Release (NVIDIA Shield TV)',
            ),
        'gpu-fyi-try-android-p-pixel-2-32':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Android arm Builder',
                tester='Android FYI Release (Pixel 2)',
            ),
        'gpu-fyi-try-android-r-pixel-4-32':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Android arm Builder',
                tester='Android FYI Release (Pixel 4)',
            ),
        'gpu-fyi-try-android-pixel-6-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Android arm64 Builder',
                tester='Android FYI Release (Pixel 6)',
            ),
        'gpu-try-android-m-nexus-5x-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu',
                buildername='Android Release (Nexus 5X)',
            ),
        'android-pie-arm64-fyi-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android.fyi',
                buildername='android-pie-arm64-fyi-rel',
            ),
        'android-webview-pie-arm64-fyi-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android.fyi',
                buildername='Android WebView P FYI (rel)',
            ),
    },
    'tryserver.chromium.angle': {
        'android-angle-chromium-try':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.angle',
                buildername='android-angle-chromium-arm64-builder',
                tester='android-angle-chromium-arm64-nexus5x',
                retry_failed_shards=False,
            ),
        'android-angle-try':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.angle',
                buildername='android-angle-arm64-builder',
                tester='android-angle-arm64-nexus5x',
                retry_failed_shards=False,
            ),
        'android_angle_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='ANGLE GPU Android Release (Nexus 5X)',
                retry_failed_shards=False,
            ),
        'fuchsia-angle-try':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.angle',
                buildername='fuchsia-angle-builder',
                is_compile_only=True,
                include_all_triggered_testers=True,
            ),
        'ios-angle-try-intel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.angle',
                buildername='ios-angle-builder',
                tester='ios-angle-intel',
                retry_failed_shards=False,
            ),
        'linux-angle-chromium-try':
            try_spec.TrySpec.create(
                mirrors=[
                    try_spec.TryMirror.create(
                        builder_group='chromium.angle',
                        buildername='linux-angle-chromium-builder',
                        tester='linux-angle-chromium-intel',
                    ),
                    try_spec.TryMirror.create(
                        builder_group='chromium.angle',
                        buildername='linux-angle-chromium-builder',
                        tester='linux-angle-chromium-nvidia',
                    ),
                ],
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
        'linux-angle-try':
            try_spec.TrySpec.create(
                mirrors=[
                    try_spec.TryMirror.create(
                        builder_group='chromium.angle',
                        buildername='linux-angle-builder',
                        tester='linux-angle-intel',
                    ),
                    try_spec.TryMirror.create(
                        builder_group='chromium.angle',
                        buildername='linux-angle-builder',
                        tester='linux-angle-nvidia',
                    ),
                ],
                retry_failed_shards=False,
            ),
        'mac-angle-chromium-try':
            try_spec.TrySpec.create(
                mirrors=[
                    try_spec.TryMirror.create(
                        builder_group='chromium.angle',
                        buildername='mac-angle-chromium-builder',
                        tester='mac-angle-chromium-amd',
                    ),
                    try_spec.TryMirror.create(
                        builder_group='chromium.angle',
                        buildername='mac-angle-chromium-builder',
                        tester='mac-angle-chromium-intel',
                    ),
                ],
                retry_failed_shards=False,
            ),
        'win-angle-chromium-x64-try':
            try_spec.TrySpec.create(
                mirrors=[
                    try_spec.TryMirror.create(
                        builder_group='chromium.angle',
                        buildername='win-angle-chromium-x64-builder',
                        tester='win10-angle-chromium-x64-intel',
                    ),
                    try_spec.TryMirror.create(
                        builder_group='chromium.angle',
                        buildername='win-angle-chromium-x64-builder',
                        tester='win10-angle-chromium-x64-nvidia',
                    ),
                ],
                retry_failed_shards=False,
            ),
        'win-angle-chromium-x86-try':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.angle',
                buildername='win-angle-chromium-x86-builder',
                tester='win7-angle-chromium-x86-amd',
                retry_failed_shards=False,
            ),
        'win-angle-x64-try':
            try_spec.TrySpec.create(
                mirrors=[
                    try_spec.TryMirror.create(
                        builder_group='chromium.angle',
                        buildername='win-angle-x64-builder',
                        tester='win10-angle-x64-intel',
                    ),
                    try_spec.TryMirror.create(
                        builder_group='chromium.angle',
                        buildername='win-angle-x64-builder',
                        tester='win10-angle-x64-nvidia',
                    ),
                ],
                retry_failed_shards=False,
            ),
        'fuchsia-angle-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Fuchsia Builder',
                is_compile_only=True,
                include_all_triggered_testers=True,
            ),
    },
    # The config for the following builders is now specified src-side in
    # //infra/config/subprojects/chromium/try/tryserver.chromium.linux.star
    # * gpu-try-linux-nvidia-rel
    # * linux-1mbu-compile-fyi-rel
    # * linux-dcheck-off-rel
    # * linux-gcc-rel
    # * linux-inverse-fieldtrials-fyi-rel
    # * linux-mbi-mode-per-render-process-host-rel
    # * linux-mbi-mode-per-site-instance-host-rel
    # * linux-rel-warmed
    # * linux-rel
    # * linux_chromium_compile_dbg_ng
    # * linux_chromium_compile_rel_ng
    # * linux_chromium_dbg_ng
    # * linux_optional_gpu_tests_rel
    'tryserver.chromium.linux': {
        'cast_shell_linux':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='Cast Linux',
            ),
        'cast_shell_linux_dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='Cast Linux Debug',
            ),
        'cast_shell_linux_arm64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='Cast Linux ARM64',
            ),
        'cast_shell_audio_linux':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='Cast Audio Linux',
            ),
        'fuchsia-fyi-arm64-femu':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='fuchsia-fyi-arm64-femu',
            ),
        'fuchsia-fyi-arm64-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='fuchsia-fyi-arm64-rel',
            ),
        'fuchsia-fyi-x64-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='fuchsia-fyi-x64-rel',
            ),
        'fuchsia-fyi-x64-wst':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='fuchsia-fyi-x64-wst',
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
        'linux-blink-heap-verification-try':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='linux-blink-heap-verification',
            ),
        'linux-example-builder':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='linux-example-builder',
            ),
        'linux-extended-tracing-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='linux-extended-tracing-rel',
            ),
        'linux-headless-shell-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='linux-headless-shell-rel',
            ),
        'linux-fieldtrial-fyi-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='linux-fieldtrial-rel',
            ),
        'linux-no-base-tracing-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='linux-no-base-tracing-rel',
            ),
        'linux-wayland-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='Linux Builder (Wayland)',
                tester='Linux Tests (Wayland)',
                regression_test_selection=try_spec.QUICK_RUN_ONLY,
            ),
        'linux-webkit-msan-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.memory',
                buildername='WebKit Linux MSAN',
            ),
        'linux_chromium_asan_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.memory',
                buildername='Linux ASan LSan Builder',
                tester='Linux ASan LSan Tests (1)',
                regression_test_selection=try_spec.QUICK_RUN_ONLY,
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
                is_compile_only=True,
                include_all_triggered_testers=True,
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
                regression_test_selection=try_spec.QUICK_RUN_ONLY,
            ),
        # TODO(crbug.com/1200904): Remove after migration
        'linux_chromium_tsan_rel_ng_bionic':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.memory',
                buildername='Linux TSan (bionic)',
            ),
        'linux_chromium_cfi_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.memory',
                buildername='Linux CFI',
            ),
        'linux_chromium_ubsan_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.memory',
                buildername='linux-ubsan-vptr',
            ),
        'linux-perfetto-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='linux-perfetto-rel',
            ),
        'linux-rel-reclient':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='Linux Builder (j-500) (reclient)',
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
        # Manually triggered GPU trybots.
        'gpu-fyi-try-lacros-amd-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Lacros x64 Builder',
                tester='Lacros FYI x64 Release (AMD)',
            ),
        'gpu-fyi-try-lacros-intel-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Lacros x64 Builder',
                tester='Lacros FYI x64 Release (Intel)',
            ),
        'gpu-fyi-try-linux-amd-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Linux Builder',
                tester='Linux FYI Release (AMD RX 5500 XT)',
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
        'gpu-fyi-try-linux-nvidia-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Linux Builder (dbg)',
                tester='Linux FYI Debug (NVIDIA)',
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
        'linux-lacros-fyi-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='linux-lacros-builder-fyi-rel',
                tester='linux-lacros-tester-fyi-rel',
            ),
        'linux-lacros-version-skew-fyi':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='linux-lacros-version-skew-fyi',
            ),
        'linux-wpt-fyi-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='linux-wpt-fyi-rel',
            ),
        'linux-wpt-identity-fyi-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='linux-wpt-identity-fyi-rel',
            ),
        'linux-wpt-input-fyi-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='linux-wpt-input-fyi-rel',
            ),
        'network_service_linux':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='Network Service Linux',
            ),
    },
    # The config for the following builders is now specified src-side in
    # //infra/config/subprojects/chromium/try/tryserver.chromium.chromiumos.star
    # * chromeos-amd64-generic-cfi-thin-lto-rel
    # * chromeos-amd64-generic-rel
    # * chromeos-arm-generic-rel
    # * chromeos-kevin-compile-rel
    # * chromeos-kevin-rel
    # * linux-chromeos-inverse-fieldtrials-fyi-rel
    # * linux-chromeos-rel
    # * linux-chromeos-rel-rts
    # * linux-lacros-dbg
    'tryserver.chromium.chromiumos': {
        'chromeos-amd64-generic-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.chromiumos',
                buildername='chromeos-amd64-generic-dbg',
            ),
        'chromeos-arm-generic-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.chromiumos',
                buildername='chromeos-arm-generic-dbg',
            ),
        'lacros-amd64-generic-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.chromiumos',
                buildername='lacros-amd64-generic-rel',
            ),
        'lacros-arm-generic-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.chromiumos',
                buildername='lacros-arm-generic-rel',
            ),
        'linux-chromeos-compile-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.chromiumos',
                buildername='linux-chromeos-dbg',
                is_compile_only=True,
                include_all_triggered_testers=True,
            ),
        'linux-chromeos-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.chromiumos',
                buildername='linux-chromeos-dbg',
            ),
        'linux-chromeos-js-code-coverage':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.chromiumos',
                buildername='linux-chromeos-js-code-coverage',
            ),
        'linux-lacros-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.chromiumos',
                buildername='linux-lacros-builder-rel',
                tester='linux-lacros-tester-rel',
            ),
        'linux-lacros-rel-code-coverage':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.chromiumos',
                buildername='linux-lacros-builder-rel',
                tester='linux-lacros-tester-rel',
            ),
        'linux-cfm-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.chromiumos',
                buildername='linux-cfm-rel',
            ),
        # Manually triggered GPU trybots.
        'gpu-fyi-try-chromeos-amd64-generic':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='ChromeOS FYI Release (amd64-generic)',
            ),
        'gpu-fyi-try-chromeos-jacuzzi-exp':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='gpu-fyi-chromeos-jacuzzi-exp',
            ),
        'gpu-fyi-try-chromeos-kevin':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='ChromeOS FYI Release (kevin)',
            ),
        'gpu-fyi-try-chromeos-octopus-exp':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='gpu-fyi-chromeos-octopus-exp',
            ),
    },
    # The config for the following builders is now specified src-side in
    # //infra/config/subprojects/chromium/try/tryserver.chromium.mac.star
    # * ios-catalyst
    # * ios-device
    # * ios-simulator
    # * ios-simulator-full-configs
    # * ios-simulator-inverse-fieldtrials-fyi
    # * ios-simulator-noncq
    # * ios-simulator-rts
    # * mac_chromium_10.11_rel_ng
    # * mac_chromium_10.12_rel_ng
    # * mac_chromium_10.13_rel_ng
    # * mac_chromium_10.14_rel_ng
    # * mac_chromium_10.15_rel_ng
    # * mac_chromium_11.0_rel_ng
    # * mac_chromium_compile_dbg_ng
    # * mac_chromium_dbg_ng
    # * mac-arm64-on-arm64-rel
    # * mac-inverse-fieldtrials-fyi-rel
    # * mac-osxbeta-rel
    # * mac-rel
    # * mac11-arm64-rel
    'tryserver.chromium.mac': {
        'ios-asan':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='ios-asan',
            ),
        'ios-simulator-cronet':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='ios-simulator-cronet',
            ),
        'ios-simulator-multi-window':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='ios-simulator-multi-window',
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
        'ios15-beta-simulator':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='ios15-beta-simulator',
            ),
        'ios15-sdk-simulator':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='ios15-sdk-simulator',
            ),
        'mac_chromium_archive_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium',
                buildername='mac-archive-rel',
            ),
        'mac-builder-next-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='Mac Builder Next',
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
            ],),
        # Manually triggered GPU trybots.
        'gpu-fyi-try-mac-amd-pro-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Mac Builder',
                tester='Mac Pro FYI Release (AMD)',
            ),
        'gpu-fyi-try-mac-amd-retina-asan':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Mac Builder (asan)',
                tester='Mac FYI Retina ASAN (AMD)',
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
        'gpu-fyi-try-mac-arm64-apple-m1-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Mac arm64 Builder',
                tester='Mac FYI Release (Apple M1)',
            ),
        'gpu-fyi-try-mac-intel-asan':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Mac Builder (asan)',
                tester='Mac FYI ASAN (Intel)',
            ),
        'gpu-fyi-try-mac-intel-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Mac Builder (dbg)',
                tester='Mac FYI Debug (Intel)',
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
    # The config for the following builders is now specified src-side in
    # //infra/config/subprojects/chromium/try/tryserver.chromium.win.star
    # * win_chromium_x64_rel_ng
    # * win_x64_archive
    # * win10_chromium_inverse_fieldtrials_x64_fyi_rel_ng
    # * win10_chromium_x64_rel_ng
    # * win11-x64-fyi-rel
    # * win_archive
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
        'win_chromium_compile_dbg_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.win',
                buildername='Win Builder (dbg)',
                is_compile_only=True,
                include_all_triggered_testers=True,
            ),
        'win_chromium_compile_rel_ng':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.win',
                buildername='Win Builder',
                is_compile_only=True,
                include_all_triggered_testers=True,
            ),
        # Optional GPU bots.
        # This trybot used to mirror "Optional Win7 Release (AMD)",
        # but that had to be disabled due to capacity constraints.
        'win_optional_gpu_tests_rel':
            try_spec.TrySpec.create(
                [
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
                ],
                retry_failed_shards=False,
            ),
        # Manually triggered GPU trybots.
        'gpu-fyi-try-win7-amd-rel-32':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Win Builder',
                tester='Win7 FYI Release (AMD)',
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
        'gpu-fyi-try-win10-amd-rel-64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.gpu.fyi',
                buildername='GPU FYI Win x64 Builder',
                tester='Win10 FYI x64 Release (AMD RX 5500 XT)',
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
        'dawn-try-mac-amd-exp':
            try_spec.TrySpec.create([
                try_spec.TryMirror.create(
                    builder_group='chromium.dawn',
                    buildername='Dawn Mac x64 Builder',
                    tester='Dawn Mac x64 Experimental Release (AMD)',
                ),
            ]),
        'dawn-try-mac-intel-exp':
            try_spec.TrySpec.create([
                try_spec.TryMirror.create(
                    builder_group='chromium.dawn',
                    buildername='Dawn Mac x64 Builder',
                    tester='Dawn Mac x64 Experimental Release (Intel)',
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
    # Rust language bots
    'tryserver.chromium.rust': {
        'android-rust-arm-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.rust',
                buildername='android-rust-arm-dbg',
            ),
        'android-rust-arm-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.rust',
                buildername='android-rust-arm-rel',
            ),
        'linux-rust-x64-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.rust',
                buildername='linux-rust-x64-dbg',
            ),
        'linux-rust-x64-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.rust',
                buildername='linux-rust-x64-rel',
            ),
        'linux-rust-x64-rel-android-toolchain':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.rust',
                buildername='linux-rust-x64-rel',
            ),
    },
    # SWANGLE bots
    'tryserver.chromium.swangle': {
        'linux-swangle-chromium-try-x64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='linux-swangle-chromium-x64',
                retry_failed_shards=False,
            ),
        'linux-swangle-try-tot-angle-x64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='linux-swangle-tot-angle-x64',
                retry_failed_shards=False,
            ),
        'linux-swangle-try-tot-swiftshader-x64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='linux-swangle-tot-swiftshader-x64',
                retry_failed_shards=False,
            ),
        'linux-swangle-try-x64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='linux-swangle-x64',
                retry_failed_shards=False,
            ),
        'mac-swangle-chromium-try-x64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='mac-swangle-chromium-x64',
                retry_failed_shards=False,
            ),
        'win-swangle-chromium-try-x86':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='win-swangle-chromium-x86',
                retry_failed_shards=False,
            ),
        'win-swangle-try-tot-angle-x64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='win-swangle-tot-angle-x64',
                retry_failed_shards=False,
            ),
        'win-swangle-try-tot-angle-x86':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='win-swangle-tot-angle-x86',
                retry_failed_shards=False,
            ),
        'win-swangle-try-tot-swiftshader-x64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='win-swangle-tot-swiftshader-x64',
                retry_failed_shards=False,
            ),
        'win-swangle-try-tot-swiftshader-x86':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='win-swangle-tot-swiftshader-x86',
                retry_failed_shards=False,
            ),
        'win-swangle-try-x64':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='win-swangle-x64',
                retry_failed_shards=False,
            ),
        'win-swangle-try-x86':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.swangle',
                buildername='win-swangle-x86',
                retry_failed_shards=False,
            ),
    },
    'tryserver.chromium.updater': {
        'win-updater-try-builder-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.updater',
                buildername='win-updater-builder-rel',
                tester='win10-updater-tester-rel',
            ),
        'mac-updater-try-builder-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.updater',
                buildername='mac-updater-builder-rel',
                tester='mac10.15-updater-tester-rel',
            ),
        'win-updater-try-builder-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.updater',
                buildername='win-updater-builder-dbg',
                tester='win10-updater-tester-dbg',
            ),
        'mac-updater-try-builder-dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.updater',
                buildername='mac-updater-builder-dbg',
                tester='mac10.15-updater-tester-dbg',
            ),
    },
    'tryserver.v8': {
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
                is_compile_only=True,
                include_all_triggered_testers=True,
            ),
        'win_chromium_compile_dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='tryserver.webrtc',
                buildername='win_chromium_compile_dbg',
                is_compile_only=True,
                include_all_triggered_testers=True,
            ),
        'mac_chromium_compile':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='tryserver.webrtc',
                buildername='mac_chromium_compile',
                is_compile_only=True,
                include_all_triggered_testers=True,
            ),
        'linux_chromium_compile':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='tryserver.webrtc',
                buildername='linux_chromium_compile',
                is_compile_only=True,
                include_all_triggered_testers=True,
            ),
        'linux_chromium_compile_dbg':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='tryserver.webrtc',
                buildername='linux_chromium_compile_dbg',
                is_compile_only=True,
                include_all_triggered_testers=True,
            ),
        'android_chromium_compile':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='tryserver.webrtc',
                buildername='android_chromium_compile',
                is_compile_only=True,
                include_all_triggered_testers=True,
            ),
    },

    # These builders don't actually exist, the configs are created to provide a
    # known set of configs for integration testing the migration tracking
    # scripts
    'tryserver.migration.testing': {
        'foo':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='migration.testing',
                buildername='foo',
            ),
        'bar':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='migration.testing',
                buildername='bar',
            ),
    },
})
