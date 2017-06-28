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
      'mac10.9_blink_dbg': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Mac Builder (dbg)',
        'tester': 'WebKit Mac10.11 (dbg)',
      }),
      'mac10.9_blink_rel': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Mac Builder',
        'tester': 'WebKit Mac10.9',
      }),
      'mac10.9_blink_compile_dbg': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Mac Builder (dbg)',
        'tester': 'WebKit Mac10.11 (dbg)',
      }, analyze_mode='compile'),
      'mac10.9_blink_compile_rel': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Mac Builder',
        'tester': 'WebKit Mac10.9',
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
      'mac10.11_retina_blink_rel': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Mac10.11 (retina)',
      }),
      'mac10.12_blink_rel': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Mac Builder',
        'tester': 'WebKit Mac10.12',
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
        'mastername': 'chromium.linux',
        'buildername': 'Android Arm64 Builder (dbg)',
      }, analyze_mode='compile'),
      'android_blink_rel': simple_bot({
        'mastername': 'chromium.webkit',
        'buildername': 'Android Builder',
        'tester': 'WebKit Android (Nexus4)',
      }),
      'android_clang_dbg_recipe': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'Android Clang Builder (dbg)',
      }, analyze_mode='compile'),
      'android_compile_dbg': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'Android Builder (dbg)',
      }, analyze_mode='compile'),
      'android_compile_mips_dbg': simple_bot({
        'mastername': 'chromium.android',
        'buildername': 'Android MIPS Builder (dbg)',
      }, analyze_mode='compile'),
      'android_compile_x64_dbg': simple_bot({
        'mastername': 'chromium.android',
        'buildername': 'Android x64 Builder (dbg)',
      }, analyze_mode='compile'),
      'android_compile_x86_dbg': simple_bot({
        'mastername': 'chromium.android',
        'buildername': 'Android x86 Builder (dbg)',
      }, analyze_mode='compile'),
      'android_compile_rel': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'Android Builder',
      }, analyze_mode='compile'),
      'android_coverage': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'Android Coverage (dbg)'
      }),
      'android_cronet': simple_bot({
        'mastername': 'chromium.android',
        'buildername': 'Android Cronet Builder'
      }),
      'android_n5x_swarming_dbg': simple_bot({
        'mastername': 'chromium.android',
        'buildername': 'Android arm64 Builder (dbg)',
        'tester': 'Marshmallow 64 bit Tester',
       }),
      'android_n5x_swarming_rel': simple_bot({
        'mastername': 'chromium.android',
        'buildername': 'Android N5X Swarm Builder',
      }),
      'android_optional_gpu_tests_rel': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Android Release (Nexus 5X)',
      }),
      'cast_shell_android': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'Cast Android (dbg)',
      }),
      'linux_android_dbg_ng': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'Android Builder (dbg)',
        'tester': 'Android Tests (dbg)',
      }),
      'linux_android_rel_ng': simple_bot({
        'mastername': 'chromium.linux',
        'buildername': 'Android Builder',
        'tester': 'Android Tests',
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
        'buildername': 'Android Release (Nexus 5X)',
      }),
      'linux_angle_rel_ng': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU Linux Builder',
        'tester': 'Linux Release (NVIDIA)',
      }),
      'linux_angle_dbg_ng': simple_bot({
        # This bot is compile-only.
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU Linux Builder (dbg)',
      }),
      'linux_angle_chromeos_rel_ng': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'Linux ChromiumOS Builder',
      }),
      'mac_angle_rel_ng': {
        'bot_ids': [
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU Mac Builder',
            'tester': 'Mac Release (Intel)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU Mac Builder',
            'tester': 'Mac Retina Release (NVIDIA)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU Mac Builder',
            'tester': 'Mac Retina Release (AMD)',
          },
        ],
      },
      'mac_angle_dbg_ng': simple_bot({
        # This bot is compile-only.
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU Mac Builder (dbg)',
      }),
      'win_angle_rel_ng': {
        'bot_ids': [
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU Win Builder',
            'tester': 'Win7 Release (NVIDIA)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU Win Builder',
            'tester': 'Win7 Release (AMD)',
          },
        ],
      },
      'win_angle_dbg_ng': simple_bot({
        # This bot is compile-only.
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU Win Builder (dbg)',
      }),
      'win_angle_x64_rel_ng': simple_bot({
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU Win x64 Builder',
        'tester': 'Win7 x64 Release (NVIDIA)',
      }),
      'win_angle_x64_dbg_ng': simple_bot({
        # This bot is compile-only.
        'mastername': 'chromium.gpu.fyi',
        'buildername': 'GPU Win x64 Builder (dbg)',
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
      'fuchsia': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'Fuchsia',
      }),
      'linux_arm': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'Linux ARM',
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
      'linux_chromium_chromeos_dbg_ng': simple_bot({
        'mastername': 'chromium.chromiumos',
        'buildername': 'Linux ChromiumOS Builder (dbg)',
        'tester': 'Linux ChromiumOS Tests (dbg)(1)',
      }),
      'linux_chromium_chromeos_compile_dbg_ng': simple_bot({
        'mastername': 'chromium.chromiumos',
        'buildername': 'Linux ChromiumOS Builder (dbg)',
      }, analyze_mode='compile'),
      'linux_chromium_chromeos_rel_ng': simple_bot({
        'mastername': 'chromium.chromiumos',
        'buildername': 'Linux ChromiumOS Builder',
        'tester': 'Linux ChromiumOS Tests (1)',
      }),
      'linux_chromium_chromeos_asan_rel_ng': simple_bot({
        'mastername': 'chromium.memory',
        'buildername': 'Linux Chromium OS ASan LSan Builder',
        'tester': 'Linux Chromium OS ASan LSan Tests (1)',
      }),
      'chromeos_amd64-generic': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'ChromiumOS amd64-generic Dummy Builder',
      }),
      'chromeos_amd64-generic_chromium_compile_only_ng': simple_bot({
        'mastername': 'chromium.chromiumos',
        'buildername': 'ChromiumOS amd64-generic Compile',
      }, analyze_mode='compile'),
      'chromeos_daisy': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'ChromiumOS daisy Dummy Builder',
      }),
      'chromeos_daisy_chromium_compile_only_ng': simple_bot({
        'mastername': 'chromium.chromiumos',
        'buildername': 'ChromiumOS daisy Compile',
      }, analyze_mode='compile'),
      'linux_chromium_chromeos_compile_rel_ng': simple_bot({
        'mastername': 'chromium.chromiumos',
        'buildername': 'Linux ChromiumOS Builder',
      }, analyze_mode='compile'),
      'linux_chromium_chromeos_msan_rel_ng': simple_bot({
        'mastername': 'chromium.memory',
        'buildername': 'Linux ChromiumOS MSan Builder',
        'tester': 'Linux ChromiumOS MSan Tests',
      }),
      'linux_chromium_chromeos_ozone_rel_ng': simple_bot({
        'mastername': 'chromium.chromiumos',
        'buildername': 'Linux ChromiumOS Ozone Builder',
        'tester': 'Linux ChromiumOS Ozone Tests (1)',
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
        'mastername': 'chromium.fyi',
        'buildername': 'CFI Linux Full',
      }),
      'linux_chromium_ubsan_rel_ng': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'UBSanVptr Linux',
      }),
      'linux_chromium_ozone_compile_only_ng': simple_bot({
        'mastername': 'chromium.fyi',
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
            'buildername': 'GPU Linux Builder',
            'tester': 'Optional Linux Release (NVIDIA)',
          },
        ],
      },
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
        'tester': 'Mac10.9 Tests (dbg)',
      }),
      'mac_chromium_rel_ng': {
        'bot_ids': [
          {
            'mastername': 'chromium.mac',
            'buildername': 'Mac Builder',
            'tester': 'Mac10.9 Tests',
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
      'mac_chromium_10.10_macviews': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'Chromium Mac 10.10 MacViews',
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
            'buildername': 'GPU Mac Builder',
            'tester': 'Optional Mac Release (Intel)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU Mac Builder',
            'tester': 'Optional Mac Retina Release (NVIDIA)',
          },
          {
            'mastername': 'chromium.gpu.fyi',
            'buildername': 'GPU Mac Builder',
            'tester': 'Optional Mac Retina Release (AMD)',
          },
        ],
      },
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
      'win_chromium_rel_ng': {
        'bot_ids': [
          {
            'mastername': 'chromium.win',
            'buildername': 'Win Builder',
            'tester': 'Win7 Tests (1)',
          },
          {
            'mastername': 'chromium.gpu',
            'buildername': 'GPU Win Builder',
            'tester': 'Win7 Release (NVIDIA)',
          },
        ],
      },
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
      'win_clang': simple_bot({
        'mastername': 'chromium.win',
        'buildername': 'WinClang64 (dbg)',
      }),
      'win_chromium_syzyasan_rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'Win SyzyAsan (rel)',
      }),
      # Experimental clang/win bots.
      'win_clang_dbg': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'CrWinClang(dbg)',
      }),
      'win_clang_rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'CrWinClang',
      }),
      'win_clang_x64_dbg': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'CrWinClang64(dbg)',
      }),
      'win_clang_x64_rel': simple_bot({
        'mastername': 'chromium.fyi',
        'buildername': 'CrWinClang64',
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
            'buildername': 'GPU Win Builder',
            'tester': 'Optional Win7 Release (NVIDIA)',
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
      'v8_android_chromium_gn_dbg': simple_bot({
        'mastername': 'client.v8.fyi',
        'buildername': 'V8 Android GN (dbg)',
      }),
    },
  },
})
