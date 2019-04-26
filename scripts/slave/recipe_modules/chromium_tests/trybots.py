# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze


def simple_bot(bot_id, analyze_mode=None):
  return {
    'bot_ids': [bot_id],
    'analyze_mode': analyze_mode,
  }


TRYBOTS = freeze({
  'tryserver.blink': {
    'builders': {
      # TODO(dpranke): Remove the _ versions of the builders once the
      # src code has been updated.
      'linux-blink-rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'linux-blink-rel-dummy',
      }),
      'linux_trusty_blink_rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'linux-blink-rel-dummy',
      }),
      'mac10.10-blink-rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'mac10.10-blink-rel-dummy',
      }),
      'mac10.10_blink_rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'mac10.10-blink-rel-dummy',
      }),
      'mac10.11-blink-rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'mac10.11-blink-rel-dummy',
      }),
      'mac10.11_blink_rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'mac10.11-blink-rel-dummy',
      }),
      'mac10.12-blink-rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'mac10.12-blink-rel-dummy',
      }),
      'mac10.12_blink_rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'mac10.12-blink-rel-dummy',
      }),
      'mac10.13_retina-blink-rel': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Mac10.13 (retina)',
      }),
      'mac10.13_retina_blink_rel': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Mac10.13 (retina)',
      }),
      'mac10.13-blink-rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'mac10.13-blink-rel-dummy',
      }),
      'mac10.13_blink_rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'mac10.13-blink-rel-dummy',
      }),
      'win7-blink-rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'win7-blink-rel-dummy',
      }),
      'win7_blink_rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'win7-blink-rel-dummy',
      }),
      'win10-blink-rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'win10-blink-rel-dummy',
      }),
      'win10_blink_rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'win10-blink-rel-dummy',
      }),
    },
  },
  'tryserver.chromium.android': {
    'builders': {
      'android-cronet-arm-dbg': simple_bot({
        'mastername': 'chromium.android',
        'buildername': 'android-cronet-arm-dbg',
      }),
      'android-kitkat-arm-rel': simple_bot({
        'mastername': 'chromium.android',
        'buildername': 'android-kitkat-arm-rel',
      }),
      'android-marshmallow-arm64-rel': {
        'bot_ids': [
          {
            'mastername': 'chromium.android',
            'buildername': 'android-marshmallow-arm64-rel',
          },
          {
            'mastername': 'chromium.gpu',
            'buildername': 'Android Release (Nexus 5X)',
          },
        ],
      },
      'android_archive_rel_ng': simple_bot({
        'mastername': 'chromium',
        'buildername': 'android-rel',
      }),
      'android_arm64_dbg_recipe': simple_bot({
        'mastername': 'chromium.android',
        'buildername': 'Android arm64 Builder (dbg)',
      }, analyze_mode='compile'),
      'android_cfi_rel_ng': simple_bot({
        'mastername': 'chromium.memory',
        'buildername': 'Android CFI',
      }),
      'android_clang_dbg_recipe': simple_bot({
        'mastername': 'chromium.android',
        'buildername': 'Android ASAN (dbg)',
      }, analyze_mode='compile'),
      'android_compile_dbg': simple_bot({
        'mastername': 'chromium.android',
        'buildername': 'Android arm Builder (dbg)',
      }, analyze_mode='compile'),
      'android_compile_x64_dbg': simple_bot({
        'mastername': 'chromium.android',
        'buildername': 'Android x64 Builder (dbg)',
      }, analyze_mode='compile'),
      'android_compile_x86_dbg': simple_bot({
        'mastername': 'chromium.android',
        'buildername': 'Android x86 Builder (dbg)',
      }, analyze_mode='compile'),
      'android_cronet': simple_bot({
        'mastername': 'chromium.android',
        'buildername': 'Android Cronet Builder'
      }),
      'android_mojo': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'Mojo Android',
      }),
      'android_n5x_swarming_dbg': simple_bot({
        'mastername': 'chromium.android',
        'buildername': 'Android arm64 Builder (dbg)',
        'tester': 'Marshmallow 64 bit Tester',
       }),
      'android_optional_gpu_tests_rel': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Optional Android Release (Nexus 5X)',
      }),
      'cast_shell_android': simple_bot({
        'mastername': 'chromium.android',
        'buildername': 'Cast Android (dbg)',
      }),
      'linux_android_dbg_ng': simple_bot({
        'mastername': 'chromium.android',
        'buildername': 'KitKat Phone Tester (dbg)',
      }),
      'android_unswarmed_pixel_aosp': simple_bot({
        'mastername': 'chromium.android',
        'buildername': 'Android WebView N (dbg)',
      }),
      # Manually triggered GPU trybots.
      'gpu-manual-try-android-l-nexus-5-32': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Android FYI Release (Nexus 5)',
      }),
      'gpu-manual-try-android-l-nexus-6-32': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Android FYI Release (Nexus 6)',
      }),
      'gpu-manual-try-android-m-nexus-6p-64': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Android FYI Release (Nexus 6P)',
      }),
      'gpu-manual-try-android-m-nexus-9-64': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Android FYI Release (Nexus 9)',
      }),
      'gpu-manual-try-android-n-nvidia-shield-tv-64': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Android FYI Release (NVIDIA Shield TV)',
      }),
      'gpu-manual-try-android-p-pixel-2-32': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Android FYI Release (Pixel 2)',
      }),
      'gpu-manual-try-android-p-pixel-2-32-vk': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Android FYI 32 Vk Release (Pixel 2)',
      }),
      'gpu-manual-try-android-p-pixel-2-32-deqp-vk': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Android FYI 32 dEQP Vk Release (Pixel 2)',
      }),
      'gpu-manual-try-android-p-pixel-2-64-vk': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Android FYI 64 Vk Release (Pixel 2)',
      }),
      'gpu-manual-try-android-p-pixel-2-64-deqp-vk': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Android FYI 64 dEQP Vk Release (Pixel 2)',
      }),
      'gpu-manual-try-android-p-pixel-xl-32-vk': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Android FYI 32 Vk Release (Pixel XL)',
      }),
      'gpu-manual-try-android-p-pixel-xl-32-deqp-vk': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Android FYI 32 dEQP Vk Release (Pixel XL)',
      }),
      'gpu-manual-try-android-p-pixel-xl-64-vk': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Android FYI 64 Vk Release (Pixel XL)',
      }),
      'gpu-manual-try-android-p-pixel-xl-64-deqp-vk': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Android FYI 64 dEQP Vk Release (Pixel XL)',
      }),
      'try-nougat-phone-tester': simple_bot({
        'mastername': 'chromium.android',
        'buildername': 'Android arm64 Builder (dbg)',
        'tester': 'Nougat Phone Tester',
      }),
    },
  },
  'tryserver.chromium.angle': {
    'builders': {
      'android_angle_rel_ng': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Android FYI Release (Nexus 5X)',
      }),
      'android_angle_vk32_rel_ng': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Android FYI 32 Vk Release (Pixel 2)',
      }),
      'android_angle_vk64_rel_ng': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Android FYI 64 Vk Release (Pixel 2)',
      }),
      'android_angle_deqp_rel_ng': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Android FYI dEQP Release (Nexus 5X)',
      }),
      'android_angle_vk32_deqp_rel_ng': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Android FYI 32 dEQP Vk Release (Pixel 2)',
      }),
      'android_angle_vk64_deqp_rel_ng': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Android FYI 64 dEQP Vk Release (Pixel 2)',
      }),
      'linux-angle-rel': {
        'bot_ids': [
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Linux Builder',
            'tester': 'ANGLE GPU Linux Release (NVIDIA)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Linux Builder',
            'tester': 'ANGLE GPU Linux Release (Intel HD 630)',
          },
        ],
      },
      # TODO(fjhenigman): Add Ozone testers when possible.
      'linux_angle_ozone_rel_ng': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Linux Ozone Builder',
      }, analyze_mode='compile'),
      'linux_angle_deqp_rel_ng': {
        'bot_ids': [
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Linux dEQP Builder',
            'tester': 'Linux FYI dEQP Release (NVIDIA)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Linux dEQP Builder',
            'tester': 'Linux FYI dEQP Release (Intel HD 630)',
          },
        ],
      },
      'mac-angle-rel': {
        'bot_ids': [
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Mac Builder',
            'tester': 'ANGLE GPU Mac Release (Intel)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Mac Builder',
            'tester': 'ANGLE GPU Mac Retina Release (NVIDIA)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Mac Builder',
            'tester': 'ANGLE GPU Mac Retina Release (AMD)',
          },
        ],
      },
      'win-angle-rel': {
        'bot_ids': [
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Win Builder',
            'tester': 'ANGLE GPU Win10 Release (NVIDIA)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Win Builder',
            'tester': 'ANGLE GPU Win10 Release (Intel HD 630)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Win Builder',
            'tester': 'Win7 ANGLE Tryserver (AMD)',
          },
        ],
      },
      'win_angle_deqp_rel_ng': {
        'bot_ids': [
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Win dEQP Builder',
            'tester': 'Win10 FYI dEQP Release (NVIDIA)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Win dEQP Builder',
            'tester': 'Win7 FYI dEQP Release (AMD)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Win dEQP Builder',
            'tester': 'Win10 FYI dEQP Release (Intel HD 630)',
          },
        ],
      },
    },
  },
  'tryserver.chromium.chrome': {
    'builders': {
        'linux-chromeos-chrome': simple_bot({
          'mastername': 'chromium.chrome',
          'buildername': 'linux-chromeos-google-rel',
        }),
    },
  },
  'tryserver.chromium.linux': {
    'builders': {
      'cast_shell_linux': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'Cast Linux',
      }),
      'cast_shell_audio_linux': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'Cast Audio Linux',
      }),
      'fuchsia_arm64': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'Fuchsia ARM64',
      }),
      'fuchsia-arm64-cast': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'fuchsia-arm64-cast',
      }),
      'fuchsia_arm64_cast_audio': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'Fuchsia ARM64 Cast Audio',
      }),
      'fuchsia-fyi-arm64-rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'fuchsia-fyi-arm64-rel',
      }),
      'fuchsia-fyi-x64-dbg': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'fuchsia-fyi-x64-dbg',
      }),
      'fuchsia-fyi-x64-rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'fuchsia-fyi-x64-rel',
      }),
      'fuchsia_x64': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'Fuchsia x64',
      }),
      'fuchsia-x64-cast': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'fuchsia-x64-cast',
      }),
      'fuchsia_x64_cast_audio': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'Fuchsia x64 Cast Audio',
      }),
      'linux-annotator-rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'linux-annotator-rel',
      }),
      'linux-blink-heap-concurrent-marking-tsan-rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'linux-blink-heap-concurrent-marking-tsan-rel',
      }),
      'linux-blink-heap-verification-try': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'linux-blink-heap-verification',
      }),
      # This trybot mirrors linux-rel
      'linux-dcheck-off-rel': {
        'bot_ids': [
          {
            'mastername': 'chromium.linux',
            'buildername': 'Linux Builder',
            'tester': 'Linux Tests',
          },
          {
            'mastername': 'chromium.gpu',
            'buildername': 'GPU Linux Builder',
            'tester': 'Linux Release (NVIDIA)',
          },
        ],
      },
      'linux-goma-rbe-staging-rel': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'linux-goma-rbe-staging-rel',
      }, analyze_mode='compile'),
      'linux-gcc-rel': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'linux-gcc-rel',
      }),
      'linux-jumbo-rel': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'linux-jumbo-rel',
      }),
      'linux-ozone-rel': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'linux-ozone-rel',
      }),
      'linux-trusty-webkit-msan-rel': simple_bot({
        'mastername': 'chromium.memory',
        'buildername': 'WebKit Linux Trusty MSAN',
      }),
      'linux-xenial-rel': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'linux-xenial-rel',
      }),
      'linux_arm': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'Linux ARM',
      }),
      'linux_chromium_dbg_32_ng': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'Linux Builder (dbg)(32)',
        'tester': 'Linux Tests (dbg)(1)(32)',
      }),
      'linux_chromium_dbg_ng': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'Linux Builder (dbg)',
        'tester': 'Linux Tests (dbg)(1)',
      }),
      'linux-rel': {
        'bot_ids': [
          {
            'mastername': 'chromium.linux',
            'buildername': 'Linux Builder',
            'tester': 'Linux Tests',
          },
          {
            'mastername': 'chromium.gpu',
            'buildername': 'GPU Linux Builder',
            'tester': 'Linux Release (NVIDIA)',
          },
        ],
      },
      'linux_chromium_asan_rel_ng': simple_bot({
        'mastername': 'chromium.memory',
        'buildername': 'Linux ASan LSan Builder',
        'tester': 'Linux ASan LSan Tests (1)',
      }),
      'linux_chromium_compile_dbg_ng': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'Linux Builder (dbg)',
      }, analyze_mode='compile'),
      'linux_chromium_compile_rel_ng': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'Linux Builder',
      }, analyze_mode='compile'),
      'linux_chromium_archive_rel_ng': simple_bot({
        'mastername': 'chromium',
        'buildername': 'linux-rel',
      }),
      'linux_chromium_clobber_rel_ng': simple_bot({
        'mastername': 'chromium',
        'buildername': 'linux-rel',
      }, analyze_mode='compile'),
      'linux_chromium_chromeos_asan_rel_ng': simple_bot({
        'mastername': 'chromium.memory',
        'buildername': 'Linux Chromium OS ASan LSan Builder',
        'tester': 'Linux Chromium OS ASan LSan Tests (1)',
      }),
      'linux_chromium_chromeos_msan_rel_ng': simple_bot({
        'mastername': 'chromium.memory',
        'buildername': 'Linux ChromiumOS MSan Builder',
        'tester': 'Linux ChromiumOS MSan Tests',
      }),
      'linux_chromium_compile_dbg_32_ng': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'Linux Builder (dbg)(32)',
      }, analyze_mode='compile'),
      'linux_chromium_msan_rel_ng': simple_bot({
        'mastername': 'chromium.memory',
        'buildername': 'Linux MSan Builder',
        'tester': 'Linux MSan Tests',
      }),
      'linux_chromium_tsan_rel_ng': simple_bot({
        'mastername': 'chromium.memory',
        'buildername': 'Linux TSan Builder',
        'tester': 'Linux TSan Tests',
      }),
      'linux_chromium_cfi_rel_ng': simple_bot({
        'mastername': 'chromium.memory',
        'buildername': 'Linux CFI',
      }),
      'linux_chromium_ubsan_rel_ng': simple_bot({
        'mastername': 'chromium.clang',
        'buildername': 'UBSanVptr Linux',
      }),
      'linux_layout_tests_composite_after_paint': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'WebKit Linux composite_after_paint Dummy Builder',
      }),
      # TODO(crbug.com/909899): Remove this after crrev.com/c/1367655 lands.
      'linux_layout_tests_slimming_paint_v2': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'WebKit Linux slimming_paint_v2 Dummy Builder',
      }),
      'linux_layout_tests_layout_ng': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'WebKit Linux layout_ng Dummy Builder',
      }),
      'linux_mojo': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'Mojo Linux',
      }),
      'linux_mojo_chromeos': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'Mojo ChromiumOS',
      }),
      'linux_vr': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'VR Linux',
      }),
      'leak_detection_linux': simple_bot({
          'mastername': 'chromium.linux',
          'buildername': 'Leak Detection Linux',
      }),
      'layout_test_leak_detection': simple_bot({
          'mastername': 'chromium.webkit',
          'buildername': 'WebKit Linux Trusty Leak',
      }),
      # Optional GPU bots.
      'linux_optional_gpu_tests_rel': {
        'bot_ids': [
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Linux Builder DEPS ANGLE',
            'tester': 'Optional Linux Release (NVIDIA)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Linux Builder DEPS ANGLE',
            'tester': 'Optional Linux Release (Intel HD 630)',
          },
        ],
      },
      # Manually triggered GPU trybots.
      'gpu-manual-try-linux-amd-rel': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Linux Builder',
        'tester': 'Linux FYI Release (AMD R7 240)',
      }),
      'gpu-manual-try-linux-intel-dqp': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Linux dEQP Builder',
        'tester': 'Linux FYI dEQP Release (Intel HD 630)',
      }),
      'gpu-manual-try-linux-intel-exp': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Linux Builder',
        'tester': 'Linux FYI Experimental Release (Intel HD 630)',
      }),
      'gpu-manual-try-linux-intel-ozn': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Linux Ozone Builder',
        'tester': 'Linux FYI Ozone (Intel)',
      }),
      'gpu-manual-try-linux-intel-rel': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Linux Builder',
        'tester': 'Linux FYI Release (Intel HD 630)',
      }),
      'gpu-manual-try-linux-nvidia-dbg': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Linux Builder (dbg)',
        'tester': 'Linux FYI Debug (NVIDIA)',
      }),
      'gpu-manual-try-linux-nvidia-dqp': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Linux dEQP Builder',
        'tester': 'Linux FYI dEQP Release (NVIDIA)',
      }),
      'gpu-manual-try-linux-nvidia-exp': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Linux Builder',
        'tester': 'Linux FYI Experimental Release (NVIDIA)',
      }),
      'gpu-manual-try-linux-nvidia-rel': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Linux Builder',
        'tester': 'Linux FYI Release (NVIDIA)',
      }),
      'gpu-manual-try-linux-nvidia-tsn': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Linux FYI GPU TSAN Release',
      }),
    },
  },
  'tryserver.chromium.chromiumos': {
    'builders': {
      'chromeos-amd64-generic-cfi-thin-lto-rel': simple_bot({
        'mastername': 'chromium.chromiumos',
        'buildername': 'chromeos-amd64-generic-cfi-thin-lto-rel',
      }),
      'chromeos-amd64-generic-rel': simple_bot({
        'mastername': 'chromium.chromiumos',
        'buildername': 'chromeos-amd64-generic-rel',
      }),
      'chromeos-daisy-rel': simple_bot({
        'mastername': 'chromium.chromiumos',
        'buildername': 'chromeos-daisy-rel',
      }),
      'chromeos-kevin-rel': simple_bot({
        'mastername': 'chromium.chromiumos',
        'buildername': 'chromeos-kevin-rel',
      }),
      'chromeos-kevin-compile-rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'chromeos-kevin-rel-hw-tests',
      }, analyze_mode='compile'),
      'linux-chromeos-compile-dbg': simple_bot({
        'mastername': 'chromium.chromiumos',
        'buildername': 'linux-chromeos-dbg',
      }, analyze_mode='compile'),
      'linux-chromeos-dbg': simple_bot({
        'mastername': 'chromium.chromiumos',
        'buildername': 'linux-chromeos-dbg',
      }),
      'linux-chromeos-rel': simple_bot({
        'mastername': 'chromium.chromiumos',
        'buildername': 'linux-chromeos-rel',
      }),
    },
  },
  'tryserver.chromium.mac': {
    'builders': {
      'mac-jumbo-rel': simple_bot({
        'mastername': 'chromium.mac',
        'buildername': 'mac-jumbo-rel',
      }),
      'mac_chromium_archive_rel_ng': simple_bot({
        'mastername': 'chromium',
        'buildername': 'mac-rel',
      }),
      'mac_chromium_dbg_ng': simple_bot({
        'mastername': 'chromium.mac',
        'buildername': 'Mac Builder (dbg)',
        'tester': 'Mac10.13 Tests (dbg)',
      }),
      'mac-rel': {
        'bot_ids': [
          {
            'mastername': 'chromium.mac',
            'buildername': 'Mac Builder',
            'tester': 'mac-dummy-rel',
          },
          {
            'mastername': 'chromium.gpu',
            'buildername': 'GPU Mac Builder',
            'tester': 'Mac Release (Intel)',
          },
          {
            'mastername': 'chromium.gpu',
            'buildername': 'GPU Mac Builder',
            'tester': 'Mac Retina Release (AMD)',
          },
        ],
      },
      'mac_chromium_10.12_rel_ng': simple_bot({
        'mastername': 'chromium.mac',
        'buildername': 'Mac Builder',
        'tester': 'Mac10.12 Tests',
      }),
      'mac_chromium_10.13_rel_ng': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'Chromium Mac 10.13',
      }),
      'mac_chromium_10.10': simple_bot({
        'mastername': 'chromium.mac',
        'buildername': 'Mac Builder',
        'tester': 'Mac10.10 Tests',
      }),
      'mac_chromium_compile_dbg_ng': simple_bot({
        'mastername': 'chromium.mac',
        'buildername': 'Mac Builder (dbg)',
      }, analyze_mode='compile'),
      'mac_chromium_compile_rel_ng': simple_bot({
        'mastername': 'chromium.mac',
        'buildername': 'Mac Builder',
      }, analyze_mode='compile'),
      'mac_chromium_asan_rel_ng': simple_bot({
        'mastername': 'chromium.memory',
        'buildername': 'Mac ASan 64 Builder',
        'tester': 'Mac ASan 64 Tests (1)',
      }),
      # Optional GPU bots.
      'mac_optional_gpu_tests_rel': {
        'bot_ids': [
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Mac Builder DEPS ANGLE',
            'tester': 'Optional Mac Release (Intel)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Mac Builder DEPS ANGLE',
            'tester': 'Optional Mac Retina Release (NVIDIA)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Mac Builder DEPS ANGLE',
            'tester': 'Optional Mac Retina Release (AMD)',
          },
        ],
      },
      # Manually triggered GPU trybots.
      'gpu-fyi-try-mac-amd-10.14': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Mac Builder',
        'tester': 'Mac FYI 10.14 Release (AMD)',
      }),
      'gpu-fyi-try-mac-amd-dqp': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Mac dEQP Builder',
        'tester': 'Mac FYI dEQP Release AMD',
      }),
      'gpu-fyi-try-mac-amd-pro-rel': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Mac Builder',
        'tester': 'Mac Pro FYI Release (AMD)',
      }),
      'gpu-fyi-try-mac-amd-retina-dbg': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Mac Builder (dbg)',
        'tester': 'Mac FYI Retina Debug (AMD)',
      }),
      'gpu-fyi-try-mac-amd-retina-exp': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Mac Builder',
        'tester': 'Mac FYI Experimental Retina Release (AMD)',
      }),
      'gpu-fyi-try-mac-amd-retina-rel': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Mac Builder',
        'tester': 'Mac FYI Retina Release (AMD)',
      }),
      'gpu-fyi-try-mac-asan': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Mac FYI GPU ASAN Release',
      }),
      'gpu-fyi-try-mac-intel-10.14': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Mac Builder',
        'tester': 'Mac FYI 10.14 Release (Intel)',
      }),
      'gpu-fyi-try-mac-intel-dbg': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Mac Builder (dbg)',
        'tester': 'Mac FYI Debug (Intel)',
      }),
      'gpu-fyi-try-mac-intel-dqp': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Mac dEQP Builder',
        'tester': 'Mac FYI dEQP Release Intel',
      }),
      'gpu-fyi-try-mac-intel-exp': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Mac Builder',
        'tester': 'Mac FYI Experimental Release (Intel)',
      }),
      'gpu-fyi-try-mac-intel-rel': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Mac Builder',
        'tester': 'Mac FYI Release (Intel)',
      }),
      'gpu-fyi-try-mac-nvidia-10.14': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Mac Builder',
        'tester': 'Mac FYI 10.14 Release (NVIDIA)',
      }),
      'gpu-fyi-try-mac-nvidia-retina-dbg': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Mac Builder (dbg)',
        'tester': 'Mac FYI Retina Debug (NVIDIA)',
      }),
      'gpu-fyi-try-mac-nvidia-retina-exp': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Mac Builder',
        'tester': 'Mac FYI Experimental Retina Release (NVIDIA)',
      }),
      'gpu-fyi-try-mac-nvidia-retina-rel': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Mac Builder',
        'tester': 'Mac FYI Retina Release (NVIDIA)',
      }),
      'gpu-try-mac-amd-retina-dbg': simple_bot({
        'mastername': 'chromium.gpu',
        'buildername': 'GPU Mac Builder (dbg)',
        'tester': 'Mac Retina Debug (AMD)',
      }),
      'gpu-try-mac-intel-dbg': simple_bot({
        'mastername': 'chromium.gpu',
        'buildername': 'GPU Mac Builder (dbg)',
        'tester': 'Mac Debug (Intel)',
      }),
    },
  },
  'tryserver.chromium.perf': {
    'builders': {
      'Android Compile Perf': simple_bot({
        'mastername': 'chromium.perf',
        'buildername': 'android-builder-perf',
      }),
      'Android arm64 Compile Perf': simple_bot({
        'mastername': 'chromium.perf',
        'buildername': 'android_arm64-builder-perf',
      }),
      'Linux Builder Perf': simple_bot({
        'mastername': 'chromium.perf',
        'buildername': 'linux-builder-perf',
      }),
      'Mac Builder Perf': simple_bot({
        'mastername': 'chromium.perf',
        'buildername': 'mac-builder-perf',
      }),
      'Win Builder Perf': simple_bot({
        'mastername': 'chromium.perf',
        'buildername': 'win32-builder-perf',
      }),
      'Win x64 Builder Perf': simple_bot({
        'mastername': 'chromium.perf',
        'buildername': 'win64-builder-perf',
      }),
    },
  },
  'tryserver.chrome.win': {
    'builders': {
      # Optional Official trybot.
      'win_chrome_official': simple_bot({
        'mastername': 'chromium.chrome',
        'buildername': 'win-google-rel',
      }),
    },
  },
  'tryserver.chromium.win': {
    'builders': {
      'win-asan': simple_bot({
        'mastername': 'chromium.memory',
        'buildername': 'win-asan',
      }),
      'win-jumbo-rel': simple_bot({
        'mastername': 'chromium.win',
        'buildername': 'win-jumbo-rel',
      }),
      'win-annotator-rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'win-annotator-rel',
      }),
      'win_archive': simple_bot({
        'mastername': 'chromium',
        'buildername': 'win32-rel',
      }),
      'win_x64_archive': simple_bot({
        'mastername': 'chromium',
        'buildername': 'win-rel',
      }),
      'win_chromium_dbg_ng': simple_bot({
        'mastername': 'chromium.win',
        'buildername': 'Win Builder (dbg)',
        'tester': 'Win7 Tests (dbg)(1)',
      }),
      'win7-rel': {
        'retry_failed_shards': True,
        'bot_ids': [
          {
            'mastername': 'chromium.win',
            'buildername': 'Win Builder',
            'tester': 'Win7 Tests (1)',
          },
          {
            'mastername': 'chromium.gpu',
            'buildername': 'GPU Win Builder',
            'tester': 'Win10 Release (NVIDIA)',
          },
        ],
      },
      'win7_chromium_rel_loc_exp': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'Win Builder Localoutputcache',
      }),
      'win10_chromium_x64_dbg_ng': simple_bot({
        'mastername': 'chromium.win',
        'buildername': 'Win x64 Builder (dbg)',
        'tester': 'Win10 Tests x64 (dbg)',
      }),
      'win10_chromium_x64_rel_ng': simple_bot({
        'mastername': 'chromium.win',
        'buildername': 'Win x64 Builder',
        'tester': 'Win10 Tests x64',
      }),
      'win_chromium_compile_dbg_ng': simple_bot({
        'mastername': 'chromium.win',
        'buildername': 'Win Builder (dbg)',
      }, analyze_mode='compile'),
      'win_chromium_compile_rel_ng': simple_bot({
        'mastername': 'chromium.win',
        'buildername': 'Win Builder',
      }, analyze_mode='compile'),
      'win_chromium_x64_rel_ng': simple_bot({
        'mastername': 'chromium.win',
        'buildername': 'Win x64 Builder',
        'tester': 'Win 7 Tests x64 (1)',
      }),
      'win_mojo': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'Mojo Windows',
      }),
      # Optional GPU bots.
      # This trybot used to mirror "Optional Win7 Release (AMD)",
      # but that had to be disabled due to capacity constraints.
      'win_optional_gpu_tests_rel': {
        'bot_ids': [
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Win Builder DEPS ANGLE',
            'tester': 'Optional Win10 Release (NVIDIA)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Win Builder DEPS ANGLE',
            'tester': 'Optional Win10 Release (Intel HD 630)',
          },
        ],
      },
      # Manually triggered GPU trybots.
      'gpu-manual-try-win7-amd-dbg': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Win Builder (dbg)',
        'tester': 'Win7 FYI Debug (AMD)',
      }),
      'gpu-manual-try-win7-amd-dqp': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Win dEQP Builder',
        'tester': 'Win7 FYI dEQP Release (AMD)',
      }),
      'gpu-manual-try-win7-amd-rel': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Win Builder',
        'tester': 'Win7 FYI Release (AMD)',
      }),
      'gpu-manual-try-win7-nvidia-dqp-64': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Win x64 dEQP Builder',
        'tester': 'Win7 FYI x64 dEQP Release (NVIDIA)',
      }),
      'gpu-manual-try-win7-nvidia-rel': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Win Builder',
        'tester': 'Win7 FYI Release (NVIDIA)',
      }),
      'gpu-manual-try-win7-nvidia-rel-64': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Win x64 Builder',
        'tester': 'Win7 FYI x64 Release (NVIDIA)',
      }),
      'gpu-manual-try-win10-intel-dqp': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Win dEQP Builder',
        'tester': 'Win10 FYI dEQP Release (Intel HD 630)',
      }),
      'gpu-manual-try-win10-intel-exp': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Win Builder',
        'tester': 'Win10 FYI Exp Release (Intel HD 630)',
      }),
      'gpu-manual-try-win10-intel-rel': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Win Builder',
        'tester': 'Win10 FYI Release (Intel HD 630)',
      }),
      'gpu-manual-try-win10-nvidia-dbg': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Win Builder (dbg)',
        'tester': 'Win10 FYI Debug (NVIDIA)',
      }),
      'gpu-manual-try-win10-nvidia-dqp': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Win dEQP Builder',
        'tester': 'Win10 FYI dEQP Release (NVIDIA)',
      }),
      'gpu-manual-try-win10-nvidia-exp': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Win Builder',
        'tester': 'Win10 FYI Exp Release (NVIDIA)',
      }),
      'gpu-manual-try-win10-nvidia-rel': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Win Builder',
        'tester': 'Win10 FYI Release (NVIDIA)',
      }),
    },
  },
  # Dawn GPU bots
  'tryserver.chromium.dawn': {
    'builders': {
      'dawn-linux-x64-deps-rel': {
        'bot_ids': [
          {
            'mastername': 'chromium.dawn',
            'buildername': 'Dawn Linux x64 DEPS Builder',
            'tester': 'Dawn Linux x64 DEPS Release (Intel HD 630)',
          },
          {
            'mastername': 'chromium.dawn',
            'buildername': 'Dawn Linux x64 DEPS Builder',
            'tester': 'Dawn Linux x64 DEPS Release (NVIDIA)',
          },
        ],
      },
      'dawn-mac-x64-deps-rel': {
        'bot_ids': [
          {
            'mastername': 'chromium.dawn',
            'buildername': 'Dawn Mac x64 DEPS Builder',
            'tester': 'Dawn Mac x64 DEPS Release (AMD)',
          },
          {
            'mastername': 'chromium.dawn',
            'buildername': 'Dawn Mac x64 DEPS Builder',
            'tester': 'Dawn Mac x64 DEPS Release (Intel)',
          },
        ],
      },
      'dawn-win10-x86-deps-rel': {
        'bot_ids': [
          {
            'mastername': 'chromium.dawn',
            'buildername': 'Dawn Win10 x86 DEPS Builder',
            'tester': 'Dawn Win10 x86 DEPS Release (Intel HD 630)',
          },
          {
            'mastername': 'chromium.dawn',
            'buildername': 'Dawn Win10 x86 DEPS Builder',
            'tester': 'Dawn Win10 x86 DEPS Release (NVIDIA)',
          },
        ],
      },
      'dawn-win10-x64-deps-rel': {
        'bot_ids': [
          {
            'mastername': 'chromium.dawn',
            'buildername': 'Dawn Win10 x64 DEPS Builder',
            'tester': 'Dawn Win10 x64 DEPS Release (Intel HD 630)',
          },
          {
            'mastername': 'chromium.dawn',
            'buildername': 'Dawn Win10 x64 DEPS Builder',
            'tester': 'Dawn Win10 x64 DEPS Release (NVIDIA)',
          },
        ],
      },
      'linux-dawn-rel': {
        'bot_ids': [
          {
            'mastername': 'chromium.dawn',
            'buildername': 'Dawn Linux x64 Builder',
            'tester': 'Dawn Linux x64 Release (Intel HD 630)',
          },
          {
            'mastername': 'chromium.dawn',
            'buildername': 'Dawn Linux x64 Builder',
            'tester': 'Dawn Linux x64 Release (NVIDIA)',
          },
        ],
      },
      'mac-dawn-rel': {
        'bot_ids': [
          {
            'mastername': 'chromium.dawn',
            'buildername': 'Dawn Mac x64 Builder',
            'tester': 'Dawn Mac x64 Release (AMD)',
          },
          {
            'mastername': 'chromium.dawn',
            'buildername': 'Dawn Mac x64 Builder',
            'tester': 'Dawn Mac x64 Release (Intel)',
          },
        ],
      },
      'win-dawn-rel': {
        'bot_ids': [
          {
            'mastername': 'chromium.dawn',
            'buildername': 'Dawn Win10 x64 Builder',
            'tester': 'Dawn Win10 x64 Release (Intel HD 630)',
          },
          {
            'mastername': 'chromium.dawn',
            'buildername': 'Dawn Win10 x64 Builder',
            'tester': 'Dawn Win10 x64 Release (NVIDIA)',
          },
        ],
      },
    },
  },
  'tryserver.v8': {
    'builders': {
      'v8_linux_blink_rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'linux-blink-rel-dummy',
      }),
      'v8_linux_chromium_gn_rel': simple_bot({
        'mastername': 'client.v8.fyi',
        'buildername': 'V8 Linux GN',
      }),
    },
  },
  'tryserver.webrtc': {
    'builders': {
      'win_chromium_compile': simple_bot({
        'mastername': 'tryserver.webrtc',
        'buildername': 'win_chromium_compile',
      }, analyze_mode='compile'),
      'mac_chromium_compile': simple_bot({
        'mastername': 'tryserver.webrtc',
        'buildername': 'mac_chromium_compile',
      }, analyze_mode='compile'),
      'linux_chromium_compile': simple_bot({
        'mastername': 'tryserver.webrtc',
        'buildername': 'linux_chromium_compile',
      }, analyze_mode='compile'),
      'android_chromium_compile': simple_bot({
        'mastername': 'tryserver.webrtc',
        'buildername': 'android_chromium_compile',
      }, analyze_mode='compile'),
    },
  },
})
