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
      'linux_trusty_blink_dbg': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Linux Trusty (dbg)',
      }),
      'linux_trusty_blink_rel': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Linux Trusty',
      }),
      'linux_trusty_blink_compile_dbg': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Linux Trusty (dbg)',
      }, analyze_mode='compile'),
      'linux_trusty_blink_compile_rel': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Linux Trusty',
      }, analyze_mode='compile'),
      'mac10.10_blink_rel': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Mac Builder',
        'tester': 'WebKit Mac10.10',
      }),
      'mac10.11_blink_rel': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Mac Builder',
        'tester': 'WebKit Mac10.11',
      }),
      'mac10.12_blink_rel': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Mac Builder',
        'tester': 'WebKit Mac10.12',
      }),
      'mac10.12_retina_blink_rel': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Mac10.12 (retina)',
      }),
      'mac10.13_blink_rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'Dummy WebKit Mac10.13',
      }),
      'win7_blink_dbg': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Win Builder (dbg)',
        'tester': 'WebKit Win7 (dbg)',
      }),
      'win7_blink_rel': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Win Builder',
        'tester': 'WebKit Win7',
      }),
      'win7_blink_compile_dbg': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Win Builder (dbg)',
        'tester': 'WebKit Win7 (dbg)'
      }, analyze_mode='compile'),
      'win7_blink_compile_rel': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Win Builder',
        'tester': 'WebKit Win7'
      }, analyze_mode='compile'),
      'win10_blink_rel': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Win Builder',
        'tester': 'WebKit Win10',
      }),
    },
  },
  'tryserver.chromium.android': {
    'builders': {
      'android_archive_rel_ng': simple_bot({
        'mastername': 'chromium',
        'buildername': 'Android',
      }),
      'android_arm64_dbg_recipe': simple_bot({
        'mastername': 'chromium.android',
        'buildername': 'Android arm64 Builder (dbg)',
      }, analyze_mode='compile'),
      'android_blink_rel': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'Android Builder',
        'tester': 'WebKit Android (Nexus4)',
      }),
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
      'android_coverage': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'Android Coverage (dbg)'
      }),
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
      'android_n5x_swarming_rel': {
        'bot_ids': [
          {
            'mastername': 'chromium.android',
            'buildername': 'Marshmallow Phone Tester (rel)',
          },
          {
            'mastername': 'chromium.gpu',
            'buildername': 'Android Release (Nexus 5X)',
          },
        ],
      },
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
      'linux_android_rel_ng': simple_bot({
        'mastername': 'chromium.android',
        'buildername': 'KitKat Phone Tester (rel)',
      }),
      'android_unswarmed_n5_rel': simple_bot({
        'mastername': 'chromium.android.fyi',
        'buildername': 'Unswarmed N5 Tests Dummy Builder',
      }),
      'android_unswarmed_n5x_rel': simple_bot({
        'mastername': 'chromium.android.fyi',
        'buildername': 'Unswarmed N5X Tests Dummy Builder',
      }),
    },
  },
  'tryserver.chromium.angle': {
    'builders': {
      'android_angle_rel_ng': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Android FYI Release (Nexus 5X)',
      }),
      'android_angle_deqp_rel_ng': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Android FYI dEQP Release (Nexus 5X)',
      }),
      'linux_angle_rel_ng': {
        'bot_ids': [
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Linux Builder',
            'tester': 'Linux FYI Release (NVIDIA)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Linux Builder',
            'tester': 'Linux FYI Release (Intel HD 630)',
          },
        ],
      },
      'linux_angle_dbg_ng': simple_bot({
        # This bot is compile-only.
        # TODO(jmadill): Remove or repurpose this config.
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Linux Builder (dbg)',
      }, analyze_mode='compile'),
      'linux_angle_compile_dbg_ng': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Linux Builder (dbg)',
      }, analyze_mode='compile'),
      # TODO(fjhenigman): Add Ozone testers when possible.
      'linux_angle_ozone_rel_ng': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Linux Ozone Builder',
      }, analyze_mode='compile'),
      'linux_angle_deqp_rel_ng': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Linux dEQP Builder',
        'tester': 'Linux FYI dEQP Release (NVIDIA)',
      }),
      'mac_angle_rel_ng': {
        'bot_ids': [
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Mac Builder',
            'tester': 'Mac FYI Release (Intel)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Mac Builder',
            'tester': 'Mac FYI Retina Release (NVIDIA)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Mac Builder',
            'tester': 'Mac FYI Retina Release (AMD)',
          },
        ],
      },
      'mac_angle_dbg_ng': simple_bot({
        # This bot is compile-only.
        # TODO(jmadill): Remove or repurpose this config.
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Mac Builder (dbg)',
      }, analyze_mode='compile'),
      'mac_angle_compile_dbg_ng': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Mac Builder (dbg)',
      }, analyze_mode='compile'),
      'win_angle_rel_ng': {
        'bot_ids': [
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Win Builder',
            'tester': 'Win10 FYI Release (NVIDIA)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Win Builder',
            'tester': 'Win7 ANGLE Tryserver (AMD)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Win Builder',
            'tester': 'Win10 FYI Release (Intel HD 630)',
          },
        ],
      },
      'win_angle_dbg_ng': simple_bot({
        # This bot is compile-only.
        # TODO(jmadill): Remove or repurpose this config.
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Win Builder (dbg)',
      }, analyze_mode='compile'),
      'win_angle_compile_dbg_ng': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Win Builder (dbg)',
      }, analyze_mode='compile'),
      'win_angle_x64_rel_ng': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Win x64 Builder',
        'tester': 'Win7 FYI x64 Release (NVIDIA)',
      }),
      'win_angle_compile_x64_rel_ng': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Win x64 Builder',
      }, analyze_mode='compile'),
      'win_angle_x64_dbg_ng': simple_bot({
        # This bot is compile-only.
        # TODO(jmadill): Remove or repurpose this config.
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Win x64 Builder (dbg)',
      }, analyze_mode='compile'),
      'win_angle_compile_x64_dbg_ng': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Win x64 Builder (dbg)',
      }, analyze_mode='compile'),
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
        ],
      },
      'win_angle_x64_deqp_rel_ng': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU FYI Win x64 dEQP Builder',
        'tester': 'Win7 FYI x64 dEQP Release (NVIDIA)',
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
      'fuchsia_arm64_cast_audio': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'Fuchsia ARM64 Cast Audio',
      }),
      'fuchsia_x64': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'Fuchsia x64',
      }),
      'fuchsia_x64_cast_audio': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'Fuchsia x64 Cast Audio',
      }),
      'linux-annotator-rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'linux-annotator-rel',
      }),
      'linux-blink-heap-verification-try': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'linux-blink-heap-verification',
      }),
      'linux_arm': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'Linux ARM',
      }),
      'linux_chromium_xenial_rel_ng': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'Linux Xenial',
      }),
      'linux_chromium_browser_side_navigation_rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'Browser Side Navigation Linux',
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
      'linux_chromium_rel_ng': {
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
        'buildername': 'Linux x64',
      }),
      'linux_chromium_clobber_rel_ng': simple_bot({
        'mastername': 'chromium',
        'buildername': 'Linux x64',
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
      'linux_chromium_headless_rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'Headless Linux (dbg)',
      }),
      'linux_chromium_cfi_rel_ng': simple_bot({
        'mastername': 'chromium.memory',
        'buildername': 'Linux CFI',
      }),
      'linux_chromium_ozone_compile_only_ng': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'Ozone Linux',
      }),
      'linux_site_isolation': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'Site Isolation Linux',
      }),
      'linux_layout_tests_slimming_paint_v2': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'WebKit Linux slimming_paint_v2 Dummy Builder',
      }),
      'linux_layout_tests_layout_ng': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'WebKit Linux layout_ng Dummy Builder',
      }),
      'linux_layout_tests_root_layer_scrolls': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'WebKit Linux root_layer_scrolls Dummy Builder',
      }),
      'linux_chromium_analysis': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'Linux Clang Analyzer',
      }),
      'linux_mojo': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'Mojo Linux',
      }),
      'linux_mojo_chromeos': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'Mojo ChromiumOS',
      }),
      # Optional GPU bots.
      'linux_optional_gpu_tests_rel': {
        'bot_ids': [
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Linux Builder',
            'tester': 'Optional Linux Release (NVIDIA)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Linux Builder',
            'tester': 'Optional Linux Release (Intel HD 630)',
          },
        ],
      },
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
    },
  },
  'tryserver.chromium.chromiumos': {
    'builders': {
      'chromeos-amd64-generic-rel': simple_bot({
        'mastername': 'chromium.chromiumos',
        'buildername': 'chromeos-amd64-generic-rel',
      }),
      'chromeos-daisy-rel': simple_bot({
        'mastername': 'chromium.chromiumos',
        'buildername': 'chromeos-daisy-rel',
      }),
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
      'mac_chromium_archive_rel_ng': simple_bot({
        'mastername': 'chromium',
        'buildername': 'Mac',
      }),
      'mac_chromium_dbg_ng': simple_bot({
        'mastername': 'chromium.mac',
        'buildername': 'Mac Builder (dbg)',
        'tester': 'Mac10.13 Tests (dbg)',
      }),
      'mac_chromium_rel_ng': {
        'bot_ids': [
          {
            'mastername': 'chromium.mac',
            'buildername': 'Mac Builder',
            'tester': 'Mac10.13 Tests',
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
          {
            'mastername': 'chromium.webkit',
            'buildername': 'WebKit Mac Builder',
            'tester': 'WebKit Mac10.12',
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
      'mac-views-rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'mac-views-rel',
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
        'deapply_patch': False,
        'bot_ids': [
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Mac Builder',
            'tester': 'Optional Mac Release (Intel)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Mac Builder',
            'tester': 'Optional Mac Retina Release (NVIDIA)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Mac Builder',
            'tester': 'Optional Mac Retina Release (AMD)',
          },
        ],
      },
    },
  },
  'tryserver.chromium.perf': {
    'builders': {
      'Android Compile': simple_bot({
        'mastername': 'chromium.perf',
        'buildername': 'Android Compile',
      }),
      'Android arm64 Compile': simple_bot({
        'mastername': 'chromium.perf',
        'buildername': 'Android arm64 Compile',
      }),
      'Linux Builder': simple_bot({
        'mastername': 'chromium.perf',
        'buildername': 'Linux Builder',
      }),
      'Mac Builder': simple_bot({
        'mastername': 'chromium.perf',
        'buildername': 'Mac Builder',
      }),
      'Win Builder': simple_bot({
        'mastername': 'chromium.perf',
        'buildername': 'Win Builder',
      }),
      'Win x64 Builder': simple_bot({
        'mastername': 'chromium.perf',
        'buildername': 'Win x64 Builder',
      }),
      # Optional One Buildbot Step Tester.
      'obbs_fyi': simple_bot({
        'mastername': 'chromium.perf.fyi',
        'buildername': 'One Buildbot Step Test Builder'
      }),
    },
  },
  'tryserver.chromium.win': {
    'builders': {
      'win_archive': simple_bot({
        'mastername': 'chromium',
        'buildername': 'Win',
      }),
      'win_x64_archive': simple_bot({
        'mastername': 'chromium',
        'buildername': 'Win x64',
      }),
      'win_chromium_dbg_ng': simple_bot({
        'mastername': 'chromium.win',
        'buildername': 'Win Builder (dbg)',
        'tester': 'Win7 Tests (dbg)(1)',
      }),
      'old_chromium_rel_ng': {
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
      'win7_chromium_rel_ng': {
        'bot_ids': [
          {
            'mastername': 'chromium.webkit',
            'buildername': 'WebKit Win Builder',
            'tester': 'WebKit Win7',
          },
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
      # TODO(crbug.com/751220): Get rid of this after it is removed from the CQ.
      'win_clang': simple_bot({
        'mastername': 'chromium.win',
        'buildername': 'WinMSVC64 (dbg)',
      }),
      'win-msvc-rel': simple_bot({
        'mastername': 'chromium.win',
        'buildername': 'WinMSVC64',
      }),
      'win-msvc-dbg': simple_bot({
        'mastername': 'chromium.win',
        'buildername': 'WinMSVC64 (dbg)',
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
            'buildername': 'GPU FYI Win Builder',
            'tester': 'Optional Win10 Release (NVIDIA)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU FYI Win Builder',
            'tester': 'Optional Win10 Release (Intel HD 630)',
          },
        ],
      },
      # Optional Official trybot.
      'win_chrome_official': simple_bot({
        'mastername': 'chromium.chrome',
        'buildername': 'Google Chrome Win',
      }),
    },
  },
  'tryserver.v8': {
    'builders': {
      'v8_linux_blink_rel': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Linux Trusty',
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
