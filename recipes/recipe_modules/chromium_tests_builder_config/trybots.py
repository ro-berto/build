# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import try_spec

# The config for the following builder groups are now specified src-side:
# * tryserver.blink
#   //infra/config/subprojects/chromium/try/tryserver.blink.star
# * tryserver.chromium
#   //infra/config/subprojects/chromium/try/tryserver.chromium.star
# * tryserver.chromium.angle
#   //infra/config/subprojects/chromium/try/tryserver.chromium.angle.star
# * trserver.chromium.chromiumos
#   //infra/config/subprojects/chromium/try/tryserver.chromium.chromiumos.star
# * tryserver.chromium.dawn
#   //infra/config/subprojects/chromium/try/tryserver.chromium.dawn.star
# * tryserver.chromium.swangle
#   //infra/config/subprojects/chromium/swangle.try.star
TRYBOTS = try_spec.TryDatabase.create({
    # The config for the following builders is now specified src-side in
    # //infra/config/subprojects/chromium/try/tryserver.chromium.android.star
    # * android_archive_rel_ng
    # * android_arm64_dbg_recipe
    # * android_compile_dbg
    # * android_compile_x64_dbg
    # * android_compile_x86_dbg
    # * android_n5x_swarming_dbg
    # * android_optional_gpu_tests_rel
    # * android_unswarmed_pixel_aosp
    # * android-10-arm64-rel
    # * android-11-x86-rel
    # * android-12-x64-dbg
    # * android-12-x64-rel
    # * android-bfcache-rel
    # * android_cronet
    # * android-cronet-arm-dbg
    # * android-cronet-x86-dbg
    # * android-cronet-x86-dbg-10-tests
    # * android-cronet-x86-dbg-11-tests
    # * android-cronet-x86-dbg-oreo-tests
    # * android-cronet-x86-dbg-pie-tests
    # * android-inverse-fieldtrials-pie-x86-fyi-rel
    # * android-oreo-arm64-dbg
    # * android-pie-arm64-rel
    # * android-pie-x86-rel
    # * android-webview-12-x64-dbg
    # * android-webview-marshmallow-arm64-dbg
    # * android-webview-nougat-arm64-dbg
    # * android-webview-oreo-arm64-dbg
    # * android-webview-pie-arm64-dbg
    # * cast_shell_android
    # * gpu-fyi-try-android-l-nexus-5-32
    # * gpu-fyi-try-android-m-nexus-5x-64
    # * gpu-fyi-try-android-nvidia-shield-tv
    # * gpu-fyi-try-android-p-pixel-2-32
    # * gpu-fyi-try-android-pixel-6-64
    # * gpu-fyi-try-android-r-pixel-4-32
    # * gpu-try-android-m-nexus-5x-64
    # * try-nougat-phone-tester
    'tryserver.chromium.android': {
        'android-asan':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.memory',
                buildername='android-asan',
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
        'android-cronet-x86-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-cronet-x86-rel',
            ),
        'android-cronet-x86-rel-kitkat-tests':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android',
                buildername='android-cronet-x86-rel',
                tester='android-cronet-x86-rel-kitkat-tests',
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
        'android-webview-pie-x86-wpt-fyi-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.android.fyi',
                buildername='android-webview-pie-x86-wpt-fyi-rel',
            ),
    },
    # The config for the following builders is now specified src-side in
    # //infra/config/subprojects/chromium/try/tryserver.chromium.linux.star
    # * cast_shell_audio_linux
    # * cast_shell_linux
    # * cast_shell_linux_arm64
    # * cast_shell_linux_dbg
    # * gpu-try-linux-nvidia-dbg
    # * gpu-try-linux-nvidia-rel
    # * gpu-fyi-try-lacros-amd-rel
    # * gpu-fyi-try-lacros-intel-rel
    # * gpu-fyi-try-linux-amd-rel
    # * gpu-fyi-try-linux-intel-exp
    # * gpu-fyi-try-linux-intel-rel
    # * gpu-fyi-try-linux-nvidia-dbg
    # * gpu-fyi-try-linux-nvidia-exp
    # * gpu-fyi-try-linux-nvidia-rel
    # * gpu-fyi-try-linux-nvidia-tsn
    # * layout_test_leak_detection
    # * linux_chromium_archive_rel_ng
    # * linux_chromium_asan_rel_ng
    # * linux_chromium_cfi_rel_ng
    # * linux_chromium_chromeos_asan_rel_ng
    # * linux_chromium_chromeos_msan_rel_ng
    # * linux_chromium_clobber_rel_ng
    # * linux_chromium_compile_dbg_ng
    # * linux_chromium_compile_rel_ng
    # * linux_chromium_dbg_ng
    # * linux_chromium_msan_rel_ng
    # * linux_chromium_tsan_rel_ng
    # * linux_chromium_ubsan_rel_ng
    # * linux_optional_gpu_tests_rel
    # * linux_vr
    # * linux-1mbu-compile-fyi-rel
    # * linux-bfcache-rel
    # * linux-dcheck-off-rel
    # * linux-extended-tracing-rel
    # * linux-gcc-rel
    # * linux-inverse-fieldtrials-fyi-rel
    # * linux-mbi-mode-per-render-process-host-rel
    # * linux-mbi-mode-per-site-instance-host-rel
    # * linux-rel
    # * linux-rel-warmed
    # * linux-wayland-rel
    # * linux-webkit-msan-rel
    # * network_service_linux
    'tryserver.chromium.linux': {
        'linux-annotator-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='linux-annotator-rel',
            ),
        'linux-blink-heap-verification-try':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='linux-blink-heap-verification',
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
        'leak_detection_linux':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.linux',
                buildername='Leak Detection Linux',
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
    },
    # The config for the following builders is now specified src-side in
    # //infra/config/subprojects/chromium/try/tryserver.chromium.mac.star
    # * gpu-fyi-try-mac-arm64-apple-m1-rel
    # * gpu-try-mac-amd-retina-dbg
    # * gpu-try-mac-intel-dbg
    # * ios-asan
    # * ios-catalyst
    # * ios-device
    # * ios-simulator
    # * ios-simulator-cronet
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
    # * mac_chromium_archive_rel_ng
    # * mac_chromium_asan_rel_ng
    # * mac_chromium_compile_dbg_ng
    # * mac_chromium_dbg_ng
    # * mac-arm64-on-arm64-rel
    # * mac-inverse-fieldtrials-fyi-rel
    # * mac-osxbeta-rel
    # * mac-rel
    # * mac11-arm64-rel
    # * mac_optional_gpu_tests_rel
    #
    # The config for the following builders is now specified src-side in
    # //infra/config/subprojects/chromium/gpu.try.star
    # * gpu-fyi-try-mac-amd-pro-rel
    # * gpu-fyi-try-mac-amd-retina-asan
    # * gpu-fyi-try-mac-amd-retina-dbg
    # * gpu-fyi-try-mac-amd-retina-exp
    # * gpu-fyi-try-mac-amd-retina-rel
    # * gpu-fyi-try-mac-intel-asan
    # * gpu-fyi-try-mac-intel-dbg
    # * gpu-fyi-try-mac-intel-exp
    # * gpu-fyi-try-mac-intel-rel
    # * gpu-fyi-try-mac-nvidia-retina-exp
    # * gpu-fyi-try-mac-nvidia-retina-rel
    'tryserver.chromium.mac': {
        'ios-simulator-multi-window':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='ios-simulator-multi-window',
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
        'mac-builder-next-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='Mac Builder Next',
            ),
    },
    # The config for the following builders is now specified src-side in
    # //infra/config/subprojects/chromium/try/tryserver.chromium.win.star
    # * win_archive
    # * win_chromium_compile_dbg_ng
    # * win_chromium_compile_rel_ng
    # * win_chromium_x64_rel_ng
    # * win_optional_gpu_tests_rel
    # * win_x64_archive
    # * win-asan
    # * win10_chromium_inverse_fieldtrials_x64_fyi_rel_ng
    # * win10_chromium_x64_dbg_ng
    # * win10_chromium_x64_rel_ng
    # * win11-x64-fyi-rel
    # * win7-rel
    #
    # The config for the following builders is now specified src-side in
    # //infra/config/subprojects/chromium/gpu.try.star
    # * gpu-fyi-try-win10-amd-rel-64
    # * gpu-fyi-try-win10-intel-exp-64
    # * gpu-fyi-try-win10-intel-rel-64
    # * gpu-fyi-try-win10-nvidia-dbg-64
    # * gpu-fyi-try-win10-nvidia-dx12vk-dbg-64
    # * gpu-fyi-try-win10-nvidia-dx12vk-rel-64
    # * gpu-fyi-try-win10-nvidia-exp-64
    # * gpu-fyi-try-win10-nvidia-rel-32
    # * gpu-fyi-try-win10-nvidia-rel-64
    'tryserver.chromium.win': {
        'win-annotator-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.fyi',
                buildername='win-annotator-rel',
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
    # The config for the following builders is now specified src-side in
    # //infra/config/subprojects/chromium/try/tryserver.chromium.updater.star
    # * mac-updater-try-builder-dbg
    # * mac-updater-try-builder-rel
    # * win-updater-try-builder-dbg
    # * win-updater-try-builder-rel
    'tryserver.chromium.updater': {},
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
