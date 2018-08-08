# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Contains the bulk of the libyuv builder configurations to improve readability
# of the recipe.

from recipe_engine.types import freeze

RECIPE_CONFIGS = freeze({
  'libyuv': {
    'chromium_config': 'libyuv',
    'gclient_config': 'libyuv',
  },
  'libyuv_clang': {
    'chromium_config': 'libyuv_clang',
    'gclient_config': 'libyuv',
  },
  'libyuv_gcc': {
    'chromium_config': 'libyuv_gcc',
    'gclient_config': 'libyuv',
  },
  'libyuv_android': {
    'chromium_config': 'libyuv_android',
    'chromium_android_config': 'libyuv',
    'gclient_config': 'libyuv_android',
  },
  'libyuv_ios': {
    'chromium_config': 'libyuv_ios',
    'gclient_config': 'libyuv_ios',
  },
})

BUILDERS = freeze({
  'client.libyuv': {
    'settings': {
      'build_gs_bucket': 'chromium-libyuv',
    },
    'builders': {
      'Win32 Debug': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'Win32 Release': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'Win64 Debug': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'Win64 Release': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'Win32 Debug (Clang)': {
        'recipe_config': 'libyuv_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'Win32 Release (Clang)': {
        'recipe_config': 'libyuv_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'Win64 Debug (Clang)': {
        'recipe_config': 'libyuv_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'Win64 Release (Clang)': {
        'recipe_config': 'libyuv_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'Mac64 Debug': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
      },
      'Mac64 Release': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
      },
      'Mac Asan': {
        'recipe_config': 'libyuv_clang',
        'chromium_apply_config': ['asan'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
      },
      'iOS Debug': {
        'recipe_config': 'libyuv_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'TARGET_ARCH': 'arm',
          'TARGET_PLATFORM': 'ios',
        },
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
      },
      'iOS Release': {
        'recipe_config': 'libyuv_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
          'TARGET_ARCH': 'arm',
          'TARGET_PLATFORM': 'ios',
        },
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
      },
      'iOS ARM64 Debug': {
        'recipe_config': 'libyuv_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
          'TARGET_ARCH': 'arm',
          'TARGET_PLATFORM': 'ios',
        },
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
      },
      'iOS ARM64 Release': {
        'recipe_config': 'libyuv_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
          'TARGET_ARCH': 'arm',
          'TARGET_PLATFORM': 'ios',
        },
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
      },
      'Linux32 Debug': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'Linux32 Release': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'Linux64 Debug': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'Linux64 Release': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'Linux GCC': {
        'recipe_config': 'libyuv_gcc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'Linux Asan': {
        'recipe_config': 'libyuv_clang',
        'chromium_apply_config': ['asan', 'lsan'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'Linux Memcheck': {
        'recipe_config': 'libyuv',
        'chromium_apply_config': ['memcheck'],
        'gclient_apply_config': ['libyuv_valgrind'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'Linux MSan': {
        'recipe_config': 'libyuv_clang',
        'chromium_apply_config': ['msan'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'Linux Tsan v2': {
        'recipe_config': 'libyuv_clang',
        'chromium_apply_config': ['tsan2'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'Linux UBSan': {
        'recipe_config': 'libyuv_clang',
        'chromium_apply_config': ['ubsan'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'Linux UBSan vptr': {
        'recipe_config': 'libyuv_clang',
        'chromium_apply_config': ['ubsan_vptr'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'Android Debug': {
        'recipe_config': 'libyuv_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
        'triggers': [
          'Android Tester ARM32 Debug (Nexus 5X)',
        ],
      },
      'Android Release': {
        'recipe_config': 'libyuv_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
        'triggers': [
          'Android Tester ARM32 Release (Nexus 5X)',
        ],
      },
      'Android ARM64 Debug': {
        'recipe_config': 'libyuv_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
        'triggers': [
          'Android Tester ARM64 Debug (Nexus 5X)',
        ],
      },
      'Android32 x86 Debug': {
        'recipe_config': 'libyuv_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'intel',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'Android32 MIPS Debug': {
        'recipe_config': 'libyuv_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'mipsel',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'Android64 x64 Debug': {
        'recipe_config': 'libyuv_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'intel',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'Android Tester ARM32 Debug (Nexus 5X)': {
        'recipe_config': 'libyuv_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android Debug',
        'testing': {'platform': 'linux'},
      },
      'Android Tester ARM32 Release (Nexus 5X)': {
        'recipe_config': 'libyuv_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android Release',
        'testing': {'platform': 'linux'},
      },
      'Android Tester ARM64 Debug (Nexus 5X)': {
        'recipe_config': 'libyuv_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android ARM64 Debug',
        'testing': {'platform': 'linux'},
      },
    },
  },
  'tryserver.libyuv': {
    'settings': {
      'build_gs_bucket': 'chromium-libyuv',
    },
    'builders': {
      'win': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'win_rel': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'win_x64_rel': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'win_clang': {
        'recipe_config': 'libyuv_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'win_clang_rel': {
        'recipe_config': 'libyuv_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'win_x64_clang_rel': {
        'recipe_config': 'libyuv_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'mac': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
      },
      'mac_rel': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
      },
      'mac_asan': {
        'recipe_config': 'libyuv_clang',
        'chromium_apply_config': ['asan'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
      },
      'ios': {
        'recipe_config': 'libyuv_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'TARGET_ARCH': 'arm',
          'TARGET_PLATFORM': 'ios',
        },
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
      },
      'ios_rel': {
        'recipe_config': 'libyuv_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
          'TARGET_ARCH': 'arm',
          'TARGET_PLATFORM': 'ios',
        },
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
      },
      'ios_arm64': {
        'recipe_config': 'libyuv_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
          'TARGET_ARCH': 'arm',
          'TARGET_PLATFORM': 'ios',
        },
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
      },
      'ios_arm64_rel': {
        'recipe_config': 'libyuv_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
          'TARGET_ARCH': 'arm',
          'TARGET_PLATFORM': 'ios',
        },
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
      },
      'linux': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'linux_rel': {
        'recipe_config': 'libyuv',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'linux_gcc': {
        'recipe_config': 'libyuv_gcc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'linux_asan': {
        'recipe_config': 'libyuv_clang',
        'chromium_apply_config': ['asan', 'lsan'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'linux_memcheck': {
        'recipe_config': 'libyuv',
        'chromium_apply_config': ['memcheck'],
        'gclient_apply_config': ['libyuv_valgrind'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'linux_msan': {
        'recipe_config': 'libyuv_clang',
        'chromium_apply_config': ['msan'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'linux_tsan2': {
        'recipe_config': 'libyuv_clang',
        'chromium_apply_config': ['tsan2'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'linux_ubsan': {
        'recipe_config': 'libyuv_clang',
        'chromium_apply_config': ['ubsan'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'linux_ubsan_vptr': {
        'recipe_config': 'libyuv_clang',
        'chromium_apply_config': ['ubsan_vptr'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'android': {
        'recipe_config': 'libyuv_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'android_rel': {
        'recipe_config': 'libyuv_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'android_arm64': {
        'recipe_config': 'libyuv_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
     'android_x86': {
        'recipe_config': 'libyuv_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'intel',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'android_x64': {
        'recipe_config': 'libyuv_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'intel',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'android_mips': {
        'recipe_config': 'libyuv_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'mipsel',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
    },
  },
})
