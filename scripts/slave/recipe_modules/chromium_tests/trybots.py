# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze


TRYBOTS = freeze({
  'tryserver.blink': {
    'builders': {
      # TODO(joelo): Remove this builder.
      'linux_blink_rel_ng': {
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Linux',
      },
      'linux_blink_dbg': {
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Linux (dbg)',
      },
      'linux_blink_rel': {
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Linux',
      },
      'linux_blink_compile_dbg': {
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Linux (dbg)',
        'analyze_mode': 'compile',
      },
      'linux_blink_compile_rel': {
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Linux',
        'analyze_mode': 'compile',
      },
      'linux_blink_oilpan_dbg': {
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Linux Oilpan (dbg)',
      },
      'linux_blink_oilpan_rel': {
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Linux Oilpan',
      },
      'linux_blink_oilpan_compile_rel': {
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Linux Oilpan',
        'analyze_mode': 'compile',
      },
      'mac_blink_dbg': {
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Mac10.7 (dbg)',
      },
      'mac_blink_rel': {
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Mac10.9',
      },
      'mac_blink_compile_dbg': {
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Mac10.7 (dbg)',
        'analyze_mode': 'compile',
      },
      'mac_blink_compile_rel': {
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Mac10.9',
        'analyze_mode': 'compile',
      },
      'mac_blink_oilpan_dbg': {
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Mac Oilpan (dbg)',
      },
      'mac_blink_oilpan_rel': {
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Mac Oilpan',
      },
      'mac_blink_oilpan_compile_rel': {
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Mac Oilpan',
        'analyze_mode': 'compile',
      },
      'win_blink_dbg': {
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Win7 (dbg)',
      },
      'win_blink_rel': {
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Win7',
      },
      'win_blink_compile_dbg': {
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Win7 (dbg)',
        'analyze_mode': 'compile',
      },
      'win_blink_compile_rel': {
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Win7',
        'analyze_mode': 'compile',
      },
      'win_blink_oilpan_dbg': {
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Win Oilpan (dbg)',
      },
      'win_blink_oilpan_rel': {
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Win Oilpan',
      },
      'win_blink_oilpan_compile_rel': {
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Win Oilpan',
        'analyze_mode': 'compile',
      },
    },
  },
  'tryserver.chromium.angle': {
    'builders': {
      'linux_angle_rel_ng': {
        'mastername': 'chromium.angle',
        'buildername': 'Linux Builder (ANGLE)',
        'tester': 'Linux Tests (ANGLE)',
      },
      'linux_angle_dbg_ng': {
        'mastername': 'chromium.angle',
        'buildername': 'Linux Builder (dbg) (ANGLE)',
        'tester': 'Linux Tests (dbg) (ANGLE)',
      },
      'mac_angle_rel_ng': {
        'mastername': 'chromium.angle',
        'buildername': 'Mac Builder (ANGLE)',
        'tester': 'Mac10.8 Tests (ANGLE)',
      },
      'mac_angle_dbg_ng': {
        'mastername': 'chromium.angle',
        'buildername': 'Mac Builder (dbg) (ANGLE)',
        'tester': 'Mac10.8 Tests (dbg) (ANGLE)',
      },
      'win_angle_rel_ng': {
        'mastername': 'chromium.angle',
        'buildername': 'Win Builder (ANGLE)',
        'tester': 'Win7 Tests (ANGLE)',
      },
      'win_angle_dbg_ng': {
        'mastername': 'chromium.angle',
        'buildername': 'Win Builder (dbg) (ANGLE)',
        'tester': 'Win7 Tests (dbg) (ANGLE)',
      },
      'win_angle_x64_rel_ng': {
        'mastername': 'chromium.angle',
        'buildername': 'Win x64 Builder (ANGLE)',
        'tester': 'Win7 Tests x64 (ANGLE)',
      },
      'win_angle_x64_dbg_ng': {
        'mastername': 'chromium.angle',
        'buildername': 'Win x64 Builder (dbg) (ANGLE)',
        'tester': 'Win7 Tests x64 (dbg) (ANGLE)',
      },
    },
  },
  'tryserver.chromium.linux': {
    'builders': {
      'android_amp': {
        'mastername': 'chromium.fyi',
        'buildername': 'Android Tests (amp split)',
      },
      'android_arm64_dbg_recipe': {
        'mastername': 'chromium.linux',
        'buildername': 'Android Arm64 Builder (dbg)',
        'analyze_mode': 'compile',
      },
      'android_clang_dbg_recipe': {
        'mastername': 'chromium.linux',
        'buildername': 'Android Clang Builder (dbg)',
        'analyze_mode': 'compile',
      },
      'android_chromium_gn_compile_dbg': {
        'mastername': 'chromium.linux',
        'buildername': 'Android GN (dbg)',
        'analyze_mode': 'compile',
      },
      'android_chromium_gn_compile_rel': {
        'mastername': 'chromium.linux',
        'buildername': 'Android GN',
        'analyze_mode': 'compile',
      },
      'android_compile_dbg': {
        'mastername': 'chromium.linux',
        'buildername': 'Android Builder (dbg)',
        'analyze_mode': 'compile',
      },
      'android_compile_rel': {
        'mastername': 'chromium.linux',
        'buildername': 'Android Builder',
        'analyze_mode': 'compile',
      },
      'android_coverage': {
        'mastername': 'chromium.fyi',
        'buildername': 'Android Coverage (dbg)'
      },
      'cast_shell_linux': {
        'mastername': 'chromium.linux',
        'buildername': 'Cast Linux',
      },
      'cast_shell_android': {
        'mastername': 'chromium.linux',
        'buildername': 'Cast Android (dbg)',
      },
      'linux_android_dbg_ng': {
        'mastername': 'chromium.linux',
        'buildername': 'Android Builder (dbg)',
        'tester': 'Android Tests (dbg)',
      },
      'linux_android_rel_ng': {
        'mastername': 'chromium.linux',
        'buildername': 'Android Builder',
        'tester': 'Android Tests',
      },
      'linux_arm_compile': {
        'mastername': 'chromium.fyi',
        'buildername': 'Linux ARM',
        'analyze_mode': 'compile',
      },
      'linux_blink_oilpan_rel': {
        'mastername': 'chromium.webkit',
        'buildername': 'WebKit Linux Oilpan',
      },
      'linux_chromium_dbg_32_ng': {
        'mastername': 'chromium.linux',
        'buildername': 'Linux Builder (dbg)(32)',
        'tester': 'Linux Tests (dbg)(1)(32)',
      },
      'linux_chromium_dbg_ng': {
        'mastername': 'chromium.linux',
        'buildername': 'Linux Builder (dbg)',
        'tester': 'Linux Tests (dbg)(1)',
      },
      'linux_chromium_gn_chromeos_dbg': {
        'mastername': 'chromium.chromiumos',
        'buildername': 'Linux ChromiumOS GN (dbg)',
      },
      'linux_chromium_gn_chromeos_rel': {
        'mastername': 'chromium.chromiumos',
        'buildername': 'Linux ChromiumOS GN',
      },
      'linux_chromium_rel_ng': {
        'mastername': 'chromium.linux',
        'buildername': 'Linux Builder',
        'tester': 'Linux Tests',
      },
      'linux_chromium_asan_rel_ng': {
        'mastername': 'chromium.memory',
        'buildername': 'Linux ASan LSan Builder',
        'tester': 'Linux ASan LSan Tests (1)',
      },
      'linux_chromium_compile_dbg_ng': {
        'mastername': 'chromium.linux',
        'buildername': 'Linux Builder (dbg)',
        'analyze_mode': 'compile',
      },
      'linux_chromium_compile_rel_ng': {
        'mastername': 'chromium.linux',
        'buildername': 'Linux Builder',
        'analyze_mode': 'compile',
      },
      'linux_chromium_clobber_rel_ng': {
        'mastername': 'chromium.fyi',
        'buildername': 'Linux Builder (clobber)',
        'analyze_mode': 'compile',
      },
      'linux_chromium_chromeos_dbg_ng': {
        'mastername': 'chromium.chromiumos',
        'buildername': 'Linux ChromiumOS Builder (dbg)',
        'tester': 'Linux ChromiumOS Tests (dbg)(1)',
      },
      'linux_chromium_chromeos_compile_dbg_ng': {
        'mastername': 'chromium.chromiumos',
        'buildername': 'Linux ChromiumOS Builder (dbg)',
        'analyze_mode': 'compile',
      },
      'linux_chromium_chromeos_rel_ng': {
        'mastername': 'chromium.chromiumos',
        'buildername': 'Linux ChromiumOS Builder',
        'tester': 'Linux ChromiumOS Tests (1)',
      },
      'linux_chromium_chromeos_asan_rel_ng': {
        'mastername': 'chromium.memory',
        'buildername': 'Linux Chromium OS ASan LSan Builder',
        'tester': 'Linux Chromium OS ASan LSan Tests (1)',
      },
      'chromeos_x86-generic_chromium_compile_only_ng': {
        'mastername': 'chromium.chromiumos',
        'buildername': 'ChromiumOS x86-generic Compile',
        'analyze_mode': 'compile',
      },
      'chromeos_amd64-generic_chromium_compile_only_ng': {
        'mastername': 'chromium.chromiumos',
        'buildername': 'ChromiumOS amd64-generic Compile',
        'analyze_mode': 'compile',
      },
      'chromeos_daisy_chromium_compile_only_ng': {
        'mastername': 'chromium.chromiumos',
        'buildername': 'ChromiumOS daisy Compile',
        'analyze_mode': 'compile',
      },
      'linux_chromium_chromeos_compile_rel_ng': {
        'mastername': 'chromium.chromiumos',
        'buildername': 'Linux ChromiumOS Builder',
        'analyze_mode': 'compile',
      },
      'linux_chromium_chromeos_msan_rel_ng': {
        'mastername': 'chromium.memory.fyi',
        'buildername': 'Chromium Linux ChromeOS MSan Builder',
        'tester': 'Linux ChromeOS MSan Tests',
      },
      'linux_chromium_chromeos_ozone_rel_ng': {
        'mastername': 'chromium.chromiumos',
        'buildername': 'Linux ChromiumOS Ozone Builder',
        'tester': 'Linux ChromiumOS Ozone Tests (1)',
      },
      'linux_chromium_compile_dbg_32_ng': {
        'mastername': 'chromium.linux',
        'buildername': 'Linux Builder (dbg)(32)',
        'analyze_mode': 'compile',
      },
      'linux_chromium_msan_rel_ng': {
        'mastername': 'chromium.memory.fyi',
        'buildername': 'Chromium Linux MSan Builder',
        'tester': 'Linux MSan Tests',
      },
      'linux_chromium_tsan_rel_ng': {
        'mastername': 'chromium.memory.fyi',
        'buildername': 'Chromium Linux TSan Builder',
        'tester': 'Linux TSan Tests',
      },
      'linux_chromium_cfi_rel_ng': {
        'mastername': 'chromium.fyi',
        'buildername': 'CFI Linux',
      },
      'linux_site_isolation': {
        'mastername': 'chromium.fyi',
        'buildername': 'Site Isolation Linux',
      },
      'linux_chromium_practice_rel_ng': {
        'mastername': 'chromium.fyi',
        'buildername': 'ChromiumPracticeFullTester',
      },
    },
  },
  'tryserver.chromium.mac': {
    'builders': {
      'mac_chromium_dbg_ng': {
        'mastername': 'chromium.mac',
        'buildername': 'Mac Builder (dbg)',
        'tester': 'Mac10.9 Tests (dbg)',
      },
      'mac_chromium_gn_dbg': {
        'mastername': 'chromium.mac',
        'buildername': 'Mac GN (dbg)',
      },
      'mac_chromium_gn_rel': {
        'mastername': 'chromium.mac',
        'buildername': 'Mac GN',
      },
      'mac_chromium_rel_ng': {
        'mastername': 'chromium.mac',
        'buildername': 'Mac Builder',
        'tester': 'Mac10.8 Tests',
      },
      'mac_chromium_10.6_rel_ng': {
        'mastername': 'chromium.mac',
        'buildername': 'Mac Builder',
        'tester': 'Mac10.6 Tests',
      },
      'mac_chromium_10.10_rel_ng': {
        'mastername': 'chromium.mac',
        'buildername': 'Mac Builder',
        'tester': 'Mac10.10 Tests',
      },
      'mac_chromium_compile_dbg_ng': {
        'mastername': 'chromium.mac',
        'buildername': 'Mac Builder (dbg)',
        'analyze_mode': 'compile',
      },
      'mac_chromium_compile_rel_ng': {
        'mastername': 'chromium.mac',
        'buildername': 'Mac Builder',
        'analyze_mode': 'compile',
      },
      'mac_chromium_asan_rel_ng': {
        'mastername': 'chromium.memory',
        'buildername': 'Mac ASan 64 Builder',
        'tester': 'Mac ASan 64 Tests (1)',
      },
    },
  },
  'tryserver.chromium.win': {
    'builders': {
      'win_chromium_dbg_ng': {
        'mastername': 'chromium.win',
        'buildername': 'Win Builder (dbg)',
        'tester': 'Win7 Tests (dbg)(1)',
      },
      'win_chromium_gn_x64_dbg': {
        'mastername': 'chromium.win',
        'buildername': 'Win x64 GN (dbg)',
      },
      'win_chromium_gn_x64_rel': {
        'mastername': 'chromium.win',
        'buildername': 'Win x64 GN',
      },
      'win_chromium_rel_ng': {
        'mastername': 'chromium.win',
        'buildername': 'Win Builder',
        'tester': 'Win7 Tests (1)',
      },
      'win_chromium_rel_ng_exp': {
        'mastername': 'chromium.win',
        'buildername': 'Win Builder',
        'tester': 'Win7 Tests (1)',
      },
      'win_chromium_xp_rel_ng': {
        'mastername': 'chromium.win',
        'buildername': 'Win Builder',
        'tester': 'XP Tests (1)',
      },
      'win_chromium_vista_rel_ng': {
        'mastername': 'chromium.win',
        'buildername': 'Win Builder',
        'tester': 'Vista Tests (1)',
      },
      'win_chromium_compile_dbg_ng': {
        'mastername': 'chromium.win',
        'buildername': 'Win Builder (dbg)',
        'analyze_mode': 'compile',
      },
      'win_chromium_compile_dbg_ng_exp': {
        'mastername': 'chromium.win',
        'buildername': 'Win Builder (dbg)',
        'analyze_mode': 'compile',
      },
      'win_chromium_compile_rel_ng': {
        'mastername': 'chromium.win',
        'buildername': 'Win Builder',
        'analyze_mode': 'compile',
      },
      'win_chromium_x64_rel_ng': {
        'mastername': 'chromium.win',
        'buildername': 'Win x64 Builder',
        'tester': 'Win 7 Tests x64 (1)',
      },
      'win_chromium_x64_rel_ng_exp': {
        'mastername': 'chromium.win',
        'buildername': 'Win x64 Builder',
        'tester': 'Win 7 Tests x64 (1)',
      },
      'win8_chromium_ng': {
        'mastername': 'chromium.win',
        'buildername': 'Win8 Aura',
      },
      'win8_chromium_gn_dbg': {
        'mastername': 'chromium.win',
        'buildername': 'Win8 GN (dbg)',
      },
      # Experimental clang/win bots.
      'win_clang_dbg': {
        'mastername': 'chromium.fyi',
        'buildername': 'CrWinClang(dbg)',
      },
      'win_clang_rel': {
        'mastername': 'chromium.fyi',
        'buildername': 'CrWinClang',
      },
      'win_clang_x64_dbg': {
        'mastername': 'chromium.fyi',
        'buildername': 'CrWinClang64(dbg)',
      },
      'win_clang_x64_rel': {
        'mastername': 'chromium.fyi',
        'buildername': 'CrWinClang64',
      },
    },
  },
})
