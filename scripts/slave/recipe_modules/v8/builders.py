# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Contains the bulk of the V8 builder configurations so they can be reused
# from multiple recipes.

from infra.libs.infra_types import freeze

BUILDERS = {
####### Waterfall: client.v8
  'client.v8': {
    'builders': {
####### Category: Linux
      'V8 Linux - builder': {
        'chromium_apply_config': ['v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux_rel_archive',
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Deopt Fuzzer',
          'V8 Linux',
          'V8 Linux - deadcode',
          'V8 Linux - gcmole',
          'V8 Linux - isolates',
          'V8 Linux - nosse3',
          'V8 Linux - nosse4',
          'V8 Linux - presubmit',
        ],
      },
      'V8 Linux - debug builder': {
        'chromium_apply_config': ['v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux_dbg_archive',
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 GC Stress - 1',
          'V8 GC Stress - 2',
          'V8 GC Stress - 3',
          'V8 Linux - debug',
          'V8 Linux - debug - avx2',
          'V8 Linux - debug - code serializer',
          'V8 Linux - debug - isolates',
          'V8 Linux - debug - nosse3',
          'V8 Linux - debug - nosse4',
          'V8 Linux - memcheck',
          'V8 Linux - test262 - debug',
          'V8 Linux - test262-es6 - debug',
          'V8 Linux - debug - greedy allocator',
        ],
      },
      'V8 Linux - nosnap builder': {
        'chromium_apply_config': ['no_snapshot', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux_nosnap_rel_archive',
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Linux - nosnap',
        ],
      },
      'V8 Linux - nosnap debug builder': {
        'chromium_apply_config': ['no_snapshot', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux_nosnap_dbg_archive',
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Linux - nosnap - debug - 1',
          'V8 Linux - nosnap - debug - 2',
        ],
      },
      'V8 Linux - presubmit': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - builder',
        'build_gs_archive': 'linux_rel_archive',
        'tests': ['presubmit'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - builder',
        'build_gs_archive': 'linux_rel_archive',
        'tests': [
          'v8initializers',
          'unittests',
          'v8testing',
          'optimize_for_size',
          'webkit',
          'benchmarks',
          'simdjs',
          'test262_variants',
          'test262_es6_variants',
          'mozilla',
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - debug': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['unittests', 'v8testing', 'benchmarks', 'mozilla',
                  'simdjs'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - debug - avx2': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['unittests', 'v8testing', 'benchmarks', 'mozilla',
                  'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - test262 - debug': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['test262_variants'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - test262-es6 - debug': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['test262_es6_variants'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - shared': {
        'chromium_apply_config': ['shared_library', 'verify_heap', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'test262', 'mozilla',
                  'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - nosnap': {
        'v8_apply_config': ['no_snapshot'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - nosnap builder',
        'build_gs_archive': 'linux_nosnap_rel_archive',
        'tests': [
          'unittests',
          'v8testing',
          'simdjs',
          'test262',
          'test262_es6',
          'mozilla',
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - nosnap - debug - 1': {
        'v8_apply_config': ['no_snapshot'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 2,
          'SHARD_RUN': 1,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - nosnap debug builder',
        'build_gs_archive': 'linux_nosnap_dbg_archive',
        'tests': ['unittests', 'v8testing', 'mozilla', 'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - nosnap - debug - 2': {
        'v8_apply_config': ['no_snapshot'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 2,
          'SHARD_RUN': 2,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - nosnap debug builder',
        'build_gs_archive': 'linux_nosnap_dbg_archive',
        'tests': ['unittests', 'v8testing', 'mozilla', 'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - isolates': {
        'v8_apply_config': ['isolates'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - builder',
        'build_gs_archive': 'linux_rel_archive',
        'tests': ['unittests', 'v8testing'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - nosse3': {
        'v8_apply_config': ['nosse3'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - builder',
        'build_gs_archive': 'linux_rel_archive',
        'tests': ['unittests', 'v8testing', 'mozilla', 'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - nosse4': {
        'v8_apply_config': ['nosse4'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - builder',
        'build_gs_archive': 'linux_rel_archive',
        'tests': ['unittests', 'v8testing', 'mozilla', 'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - deadcode': {
        'v8_apply_config': ['deadcode'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - builder',
        'build_gs_archive': 'linux_rel_archive',
        'tests': ['unittests', 'v8testing', 'test262', 'mozilla',
                  'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - debug - isolates': {
        'v8_apply_config': ['isolates'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['unittests', 'v8testing'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - debug - nosse3': {
        'v8_apply_config': ['nosse3'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['unittests', 'v8testing', 'test262', 'mozilla',
                  'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - debug - nosse4': {
        'v8_apply_config': ['nosse4'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['unittests', 'v8testing', 'test262', 'mozilla',
                  'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - gcmole': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - builder',
        'build_gs_archive': 'linux_rel_archive',
        'tests': ['gcmole'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - interpreted regexp': {
        'chromium_apply_config': ['interpreted_regexp', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - noi18n - debug': {
        'v8_apply_config': ['no_i18n'],
        'chromium_apply_config': ['no_i18n', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'webkit', 'mozilla', 'test262',
                  'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - debug - code serializer': {
        'v8_apply_config': ['code_serializer', 'no_variants'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['mjsunit', 'webkit', 'mozilla', 'test262', 'benchmarks',
                  'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - debug - greedy allocator': {
        'v8_apply_config': ['greedy_allocator', 'turbo_variant'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['unittests', 'v8testing', 'benchmarks', 'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
####### Category: Linux64
      'V8 Linux64 - builder': {
        'chromium_apply_config': ['v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux64_rel_archive',
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Linux64',
          'V8 Linux64 - avx2',
        ],
      },
      'V8 Linux64 - debug builder': {
        'chromium_apply_config': ['v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux64_dbg_archive',
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Fuzzer',
          'V8 Linux64 - debug',
          'V8 Linux64 - debug - avx2',
          'V8 Linux64 - debug - greedy allocator',
        ],
      },
      'V8 Linux64 - custom snapshot - debug builder': {
        'chromium_apply_config': ['embed_script_mjsunit', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux64_custom_snapshot_dbg_archive',
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Linux64 - custom snapshot - debug',
          'V8 Linux64 GC Stress - custom snapshot',
        ],
      },
      'V8 Linux64': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux64 - builder',
        'build_gs_archive': 'linux64_rel_archive',
        'tests': [
          'v8initializers',
          'unittests',
          'v8testing',
          'optimize_for_size',
          'webkit',
          'test262',
          'test262_es6',
          'mozilla',
          'simdjs',
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 - avx2': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux64 - builder',
        'build_gs_archive': 'linux64_rel_archive',
        'tests': [
          'unittests',
          'v8testing',
          'webkit',
          'benchmarks',
          'mozilla',
          'simdjs_small',
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 - debug': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux64 - debug builder',
        'build_gs_archive': 'linux64_dbg_archive',
        'tests': [
          'unittests',
          'v8testing',
          'webkit',
          'test262',
          'test262_es6',
          'mozilla',
          'simdjs',
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 - debug - avx2': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux64 - debug builder',
        'build_gs_archive': 'linux64_dbg_archive',
        'tests': [
          'unittests',
          'v8testing',
          'webkit',
          'benchmarks',
          'mozilla',
          'simdjs_small',
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 - custom snapshot - debug': {
        'v8_apply_config': ['no_harness'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux64 - custom snapshot - debug builder',
        'build_gs_archive': 'linux64_custom_snapshot_dbg_archive',
        'tests': ['mjsunit'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 - debug - greedy allocator': {
        'v8_apply_config': ['greedy_allocator', 'turbo_variant'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux64 - debug builder',
        'build_gs_archive': 'linux64_dbg_archive',
        'tests': ['unittests', 'v8testing', 'benchmarks', 'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
####### Category: Windows
      'V8 Win32 - builder': {
        'chromium_apply_config': ['v8_ninja', 'msvs2013'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'win32_rel_archive',
        'testing': {'platform': 'win'},
        'triggers': [
          'V8 Win32 - 1',
          'V8 Win32 - 2',
        ],
      },
      'V8 Win32 - debug builder': {
        'chromium_apply_config': ['v8_ninja', 'msvs2013'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'win32_dbg_archive',
        'testing': {'platform': 'win'},
        'triggers': [
          'V8 Win32 - debug - 1',
          'V8 Win32 - debug - 2',
          'V8 Win32 - debug - 3'
        ],
      },
      'V8 Win32 - 1': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 2,
          'SHARD_RUN': 1,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Win32 - builder',
        'build_gs_archive': 'win32_rel_archive',
        'tests': ['unittests', 'v8testing', 'webkit', 'mozilla'],
        'testing': {'platform': 'win'},
      },
      'V8 Win32 - 2': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 2,
          'SHARD_RUN': 2,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Win32 - builder',
        'build_gs_archive': 'win32_rel_archive',
        'tests': ['unittests', 'v8testing', 'webkit', 'mozilla'],
        'testing': {'platform': 'win'},
      },
      'V8 Win32 - nosnap - shared': {
        'v8_apply_config': ['no_snapshot'],
        'chromium_apply_config': [
          'v8_ninja',
          'msvs2013',
          'shared_library',
          'no_snapshot',
         ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing'],
        'testing': {'platform': 'win'},
      },
      'V8 Win32 - debug - 1': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 3,
          'SHARD_RUN': 1,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Win32 - debug builder',
        'build_gs_archive': 'win32_dbg_archive',
        'tests': ['unittests', 'v8testing', 'webkit', 'mozilla'],
        'testing': {'platform': 'win'},
      },
      'V8 Win32 - debug - 2': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 3,
          'SHARD_RUN': 2,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Win32 - debug builder',
        'build_gs_archive': 'win32_dbg_archive',
        'tests': ['unittests', 'v8testing', 'webkit', 'mozilla'],
        'testing': {'platform': 'win'},
      },
      'V8 Win32 - debug - 3': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 3,
          'SHARD_RUN': 3,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Win32 - debug builder',
        'build_gs_archive': 'win32_dbg_archive',
        'tests': ['unittests', 'v8testing', 'webkit', 'mozilla'],
        'testing': {'platform': 'win'},
      },
      'V8 Win64': {
        'chromium_apply_config': ['v8_ninja', 'msvs2013'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        # FIXME(machenbach): Add back simdjs_small once download is fixed.
        'tests': ['unittests', 'v8testing', 'webkit', 'mozilla'],
        'testing': {'platform': 'win'},
      },
      'V8 Win64 - debug': {
        'chromium_apply_config': ['v8_ninja', 'msvs2013'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        # FIXME(machenbach): Add back simdjs_small once download is fixed.
        'tests': ['unittests', 'v8testing', 'webkit', 'mozilla'],
        'testing': {'platform': 'win'},
      },
####### Category: Mac
      'V8 Mac': {
        'chromium_apply_config': ['v8_ninja', 'clang', 'goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'webkit', 'test262', 'mozilla',
                  'simdjs'],
        'testing': {'platform': 'mac'},
      },
      'V8 Mac - debug': {
        'chromium_apply_config': ['v8_ninja', 'clang', 'goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'webkit', 'test262', 'mozilla',
                  'simdjs_small'],
        'testing': {'platform': 'mac'},
      },
      'V8 Mac64': {
        'chromium_apply_config': ['v8_ninja', 'clang', 'goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'webkit', 'test262', 'mozilla',
                  'simdjs'],
        'testing': {'platform': 'mac'},
      },
      'V8 Mac64 - debug': {
        'chromium_apply_config': ['v8_ninja', 'clang', 'goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'webkit', 'test262', 'mozilla',
                  'simdjs_small'],
        'testing': {'platform': 'mac'},
      },
      'V8 Mac64 - xcode': {
        'chromium_apply_config': ['clang'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
      },
####### Category: Arm
      'V8 Arm - builder': {
        'chromium_apply_config': ['arm_hard_float'],
        'v8_apply_config': ['arm_hard_float'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'arm_rel_archive',
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Arm',
        ],
      },
      'V8 Arm - debug builder': {
        'chromium_apply_config': ['arm_hard_float'],
        'v8_apply_config': ['arm_hard_float'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'arm_dbg_archive',
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Arm - debug - 1',
          'V8 Arm - debug - 2',
          'V8 Arm GC Stress',
        ],
      },
      'V8 Android Arm - builder': {
        'gclient_apply_config': ['android'],
        'chromium_apply_config': ['v8_ninja', 'default_compiler', 'goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
          'TARGET_PLATFORM': 'android',
        },
        'bot_type': 'builder',
        'build_gs_archive': 'android_arm_rel_archive',
        'testing': {'platform': 'linux'},
      },
      'V8 Android Arm64 - builder': {
        'gclient_apply_config': ['android'],
        'chromium_apply_config': ['v8_ninja', 'default_compiler', 'goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
          'TARGET_PLATFORM': 'android',
        },
        'bot_type': 'builder',
        'build_gs_archive': 'android_arm64_rel_archive',
        'testing': {'platform': 'linux'},
      },
      'V8 Arm': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Arm - builder',
        'build_gs_archive': 'arm_rel_archive',
        'tests': [
          'unittests',
          'v8testing',
          'webkit',
          'benchmarks',
          'optimize_for_size',
          'simdjs',
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Arm - debug': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Arm - debug builder',
        'build_gs_archive': 'arm_dbg_archive',
        'tests': ['unittests', 'v8testing', 'webkit', 'optimize_for_size',
                  'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'V8 Arm - debug - 1': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 2,
          'SHARD_RUN': 1,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Arm - debug builder',
        'build_gs_archive': 'arm_dbg_archive',
        'tests': ['unittests', 'v8testing', 'webkit', 'optimize_for_size',
                  'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'V8 Arm - debug - 2': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 2,
          'SHARD_RUN': 2,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Arm - debug builder',
        'build_gs_archive': 'arm_dbg_archive',
        'tests': ['unittests', 'v8testing', 'webkit', 'optimize_for_size',
                  'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
####### Category: MIPS
      'V8 Mips - builder': {
        'chromium_apply_config': ['no_snapshot', 'no_i18n'],
        'v8_apply_config': ['mips_cross_compile', 'no_snapshot', 'no_i18n'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'mips',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'mips_rel_archive',
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Mips - big endian - nosnap - 1',
          'V8 Mips - big endian - nosnap - 2',
        ],
      },
      'V8 Mips - big endian - nosnap - 1': {
        'v8_apply_config': ['no_snapshot', 'no_i18n'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'mips',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 2,
          'SHARD_RUN': 1,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Mips - builder',
        'build_gs_archive': 'mips_rel_archive',
        'tests': ['unittests', 'v8testing', 'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'V8 Mips - big endian - nosnap - 2': {
        'v8_apply_config': ['no_snapshot', 'no_i18n'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'mips',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 2,
          'SHARD_RUN': 2,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Mips - builder',
        'build_gs_archive': 'mips_rel_archive',
        'tests': ['unittests', 'v8testing', 'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
####### Category: Simulators
      'V8 Linux - arm - sim': {
        'chromium_apply_config': ['simulate_arm', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          'unittests',
          'v8testing',
          'webkit',
          'test262',
          'test262_es6',
          'mozilla',
          'simdjs',
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm - sim - debug': {
        'chromium_apply_config': ['simulate_arm', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'webkit', 'test262', 'mozilla',
                  'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm - sim - novfp3': {
        # TODO(machenbach): Can these configs be reduced to one?
        'chromium_apply_config': ['simulate_arm', 'novfp3', 'v8_goma'],
        'v8_apply_config': ['novfp3'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'test262', 'mozilla',
                  'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm - sim - debug - novfp3': {
        'chromium_apply_config': ['simulate_arm', 'novfp3', 'v8_goma'],
        'v8_apply_config': ['novfp3'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'test262', 'mozilla',
                  'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm64 - sim': {
        'chromium_apply_config': ['simulate_arm', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          'unittests',
          'v8testing',
          'webkit',
          'test262',
          'test262_es6',
          'mozilla',
          'simdjs',
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm64 - sim - debug': {
        'chromium_apply_config': ['simulate_arm', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'webkit', 'mozilla',
                  'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm64 - sim - nosnap - debug - 1': {
        'chromium_apply_config': ['simulate_arm', 'no_snapshot', 'v8_goma'],
        'v8_apply_config': ['no_snapshot'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
          'SHARD_COUNT': 2,
          'SHARD_RUN': 1,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'webkit', 'test262', 'mozilla',
                  'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm64 - sim - nosnap - debug - 2': {
        'chromium_apply_config': ['simulate_arm', 'no_snapshot', 'v8_goma'],
        'v8_apply_config': ['no_snapshot'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
          'SHARD_COUNT': 2,
          'SHARD_RUN': 2,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'webkit', 'test262', 'mozilla',
                  'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm64 - sim - gc stress': {
        'chromium_apply_config': ['simulate_arm', 'v8_goma'],
        'v8_apply_config': ['gc_stress'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['mjsunit', 'webkit'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - mipsel - sim - builder': {
        'chromium_apply_config': ['simulate_mipsel', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'mipsel_sim_rel_archive',
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Linux - mipsel - sim',
        ],
      },
      'V8 Linux - mips64el - sim - builder': {
        'chromium_apply_config': ['simulate_mipsel', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'mips64el_sim_rel_archive',
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - mipsel - sim': {
        'chromium_apply_config': ['simulate_mipsel'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - mipsel - sim - builder',
        'build_gs_archive': 'mipsel_sim_rel_archive',
        'tests': ['unittests', 'v8testing', 'test262', 'test262_es6',
                  'simdjs'],
        'testing': {'platform': 'linux'},
      },
####### Category: Misc
      'V8 Fuzzer': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux64 - debug builder',
        'build_gs_archive': 'linux64_dbg_archive',
        'tests': ['fuzz'],
        'testing': {'platform': 'linux'},
      },
      'V8 Deopt Fuzzer': {
        'v8_apply_config': ['deopt_fuzz_normal'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - builder',
        'build_gs_archive': 'linux_rel_archive',
        'tests': ['deopt'],
        'testing': {'platform': 'linux'},
      },
      'V8 GC Stress - 1': {
        'v8_apply_config': ['gc_stress'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 3,
          'SHARD_RUN': 1,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['mjsunit', 'webkit'],
        'testing': {'platform': 'linux'},
      },
      'V8 GC Stress - 2': {
        'v8_apply_config': ['gc_stress'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 3,
          'SHARD_RUN': 2,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['mjsunit', 'webkit'],
        'testing': {'platform': 'linux'},
      },
      'V8 GC Stress - 3': {
        'v8_apply_config': ['gc_stress'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'SHARD_COUNT': 3,
          'SHARD_RUN': 3,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['mjsunit', 'webkit'],
        'testing': {'platform': 'linux'},
      },
      'V8 Mac GC Stress': {
        'chromium_apply_config': ['v8_ninja', 'clang', 'goma'],
        'v8_apply_config': ['gc_stress'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['mjsunit', 'webkit'],
        'testing': {'platform': 'mac'},
      },
      'V8 Arm GC Stress': {
        'v8_apply_config': ['gc_stress', 'no_variants'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Arm - debug builder',
        'build_gs_archive': 'arm_dbg_archive',
        'tests': ['mjsunit', 'webkit'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 GC Stress - custom snapshot': {
        'v8_apply_config': ['gc_stress', 'no_harness'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux64 - custom snapshot - debug builder',
        'build_gs_archive': 'linux64_custom_snapshot_dbg_archive',
        'tests': ['mjsunit'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux gcc 4.8': {
        'chromium_apply_config': ['no_clang'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 ASAN': {
        'chromium_apply_config': ['v8_ninja', 'clang', 'asan', 'goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing'],
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Linux64 ASAN no inline - release builder',
          'V8 Linux64 ASAN - debug builder',
          'V8 Linux64 ASAN arm64 - debug builder',
          'V8 Linux ASAN arm - debug builder',
          'V8 Linux ASAN mipsel - debug builder',
        ],
      },
      'V8 Linux64 ASAN no inline - release builder': {
        'chromium_apply_config': [
          'clang',
          'v8_ninja',
          'goma',
          'asan',
          'asan_symbolized',
          'clobber',
          'default_target_d8',
          'sanitizer_coverage',
          'v8_verify_heap',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-asan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8-asan-no-inline',
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 ASAN - debug builder': {
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'clobber',
          'default_target_d8',
          'asan',
          'goma',
          'sanitizer_coverage',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-asan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8-asan',
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 ASAN arm64 - debug builder': {
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'clobber',
          'default_target_d8',
          'asan',
          'goma',
          'sanitizer_coverage',
          'simulate_arm',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-asan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8-arm64-asan',
        'testing': {'platform': 'linux'},
      },
      'V8 Linux ASAN arm - debug builder': {
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'clobber',
          'default_target_d8',
          'asan',
          'goma',
          'sanitizer_coverage',
          'simulate_arm',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-asan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8-arm-asan',
        'testing': {'platform': 'linux'},
      },
      'V8 Linux ASAN mipsel - debug builder': {
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'clobber',
          'default_target_d8',
          'asan',
          'goma',
          'sanitizer_coverage',
          'simulate_mipsel',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-asan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8-mipsel-asan',
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 TSAN': {
        'chromium_apply_config': ['v8_ninja', 'clang', 'tsan2', 'goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm64 - sim - MSAN': {
        # 'simulate_arm' is actually implied by 'msan'. We still set it
        # explicitly for the sake of consistency.
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'msan',
          'simulate_arm',
          'goma',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - memcheck': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': ['simpleleak'],
        'testing': {'platform': 'linux'},
      },
      'V8 Mac64 ASAN': {
        'chromium_apply_config': ['v8_ninja', 'clang', 'asan', 'goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing'],
        'testing': {'platform': 'mac'},
      },
####### Category: FYI
      'V8 Linux - vtunejit': {
        'chromium_apply_config': ['vtunejit', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - x32 - nosnap - debug builder': {
        'v8_apply_config': ['no_snapshot'],
        'chromium_apply_config': ['no_snapshot', 'v8_goma', 'x32'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux_x32_nosnap_dbg_archive',
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Linux - x32 - nosnap - debug',
        ],
      },
      'V8 Linux - x32 - nosnap - debug': {
        'v8_apply_config': ['no_snapshot'],
        'chromium_apply_config': ['no_snapshot', 'v8_goma', 'x32'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - x32 - nosnap - debug builder',
        'build_gs_archive': 'linux_x32_nosnap_dbg_archive',
        'tests': ['unittests', 'v8testing'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - x87 - nosnap - debug builder': {
        'v8_apply_config': ['no_snapshot'],
        'chromium_apply_config': ['no_snapshot', 'v8_goma', 'x87'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux_x87_nosnap_dbg_archive',
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Linux - x87 - nosnap - debug',
        ],
      },
      'V8 Linux - x87 - nosnap - debug': {
        'v8_apply_config': ['no_snapshot'],
        'chromium_apply_config': ['no_snapshot', 'v8_goma', 'x87'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - x87 - nosnap - debug builder',
        'build_gs_archive': 'linux_x87_nosnap_dbg_archive',
        'tests': ['unittests', 'v8testing'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - predictable': {
        'v8_apply_config': ['predictable'],
        'chromium_apply_config': ['predictable', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['mjsunit', 'webkit', 'benchmarks', 'mozilla'],
        'testing': {'platform': 'linux'},
        'enable_bisect': True,
      },
      'V8 Linux - ppc - sim': {
        'chromium_apply_config': ['simulate_ppc', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - ppc64 - sim': {
        'chromium_apply_config': ['simulate_ppc', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing'],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - full debug': {
        'chromium_apply_config': ['no_optimized_debug', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing'],
        'testing': {'platform': 'linux'},
      },
      'V8 Random Deopt Fuzzer - debug': {
        'chromium_apply_config': ['v8_goma'],
        'v8_apply_config': ['deopt_fuzz_random'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['deopt'],
        'testing': {'platform': 'linux'},
      },
    },
  },
####### Waterfall: tryserver.v8
  'tryserver.v8': {
    'builders': {
      'v8_linux_rel': {
        'chromium_apply_config': ['v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          'unittests',
          'v8testing',
          'optimize_for_size',
          'webkit',
          'test262',
          'test262_es6',
          'mozilla',
          'simdjs',
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_avx2_dbg': {
        'chromium_apply_config': ['v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [
          'unittests',
          'v8testing',
          'webkit',
          'simdjs_small',
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_nodcheck_rel': {
        'chromium_apply_config': ['no_dcheck', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'benchmarks',
                  'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_dbg': {
        'chromium_apply_config': ['v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'webkit',
                  'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_greedy_allocator_dbg': {
        'chromium_apply_config': ['v8_goma'],
        'v8_apply_config': ['greedy_allocator', 'turbo_variant'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'benchmarks',
                  'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_nosnap_rel': {
        'chromium_apply_config': ['no_snapshot', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing'],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_nosnap_dbg': {
        'chromium_apply_config': ['no_snapshot', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing'],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_gcc_compile_rel': {
        'chromium_apply_config': ['no_dcheck', 'no_clang'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_rel': {
        'chromium_apply_config': ['v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          'v8initializers',
          'unittests',
          'v8testing',
          'optimize_for_size',
          'webkit',
          'test262_es6',
          'simdjs',
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_avx2_rel': {
        'chromium_apply_config': ['v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          'unittests',
          'v8testing',
          'webkit',
          'simdjs_small',
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_avx2_dbg': {
        'chromium_apply_config': ['v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [
          'unittests',
          'v8testing',
          'webkit',
          'simdjs_small',
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_greedy_allocator_dbg': {
        'chromium_apply_config': ['v8_goma'],
        'v8_apply_config': ['greedy_allocator', 'turbo_variant'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'benchmarks'],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_asan_rel': {
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'asan',
          'goma',
          'no_dcheck',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing'],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_msan_rel': {
        # 'simulate_arm' is actually implied by 'msan'. We still set it
        # explicitly for the sake of consistency.
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'msan',
          'simulate_arm',
          'goma',
          'no_dcheck',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing'],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_tsan_rel': {
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'tsan2',
          'goma',
          'no_dcheck',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing'],
        'testing': {'platform': 'linux'},
      },
      'v8_win_rel': {
        'chromium_apply_config': ['v8_ninja', 'msvs2013'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'webkit'],
        'testing': {'platform': 'win'},
      },
      'v8_win_dbg': {
        'chromium_apply_config': ['v8_ninja', 'msvs2013'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'webkit'],
        'testing': {'platform': 'win'},
      },
      'v8_win_compile_dbg': {
        'chromium_apply_config': ['v8_ninja', 'msvs2013'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'v8_win_nosnap_shared_compile_rel': {
        'v8_apply_config': ['no_snapshot'],
        'chromium_apply_config': [
          'v8_ninja',
          'msvs2013',
          'shared_library',
          'no_snapshot',
         ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'v8_win_nosnap_shared_rel': {
        'v8_apply_config': ['no_snapshot'],
        'chromium_apply_config': [
          'v8_ninja',
          'msvs2013',
          'no_dcheck',
          'no_snapshot',
          'shared_library',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing'],
        'testing': {'platform': 'win'},
      },
      'v8_win64_compile_rel': {
        'chromium_apply_config': ['v8_ninja', 'msvs2013'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'v8_win64_rel': {
        'chromium_apply_config': ['v8_ninja', 'msvs2013'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        # FIXME(machenbach): Add back simdjs_small once download is fixed.
        'tests': ['unittests', 'v8testing', 'webkit'],
        'testing': {'platform': 'win'},
      },
      'v8_win64_ninja_rel': {
        'chromium_apply_config': [
          'default_compiler',
          'v8_ninja',
          'goma',
          'msvs2013',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing'],
        'testing': {'platform': 'win'},
      },
      'v8_win64_dbg': {
        'chromium_apply_config': ['v8_ninja', 'msvs2013'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        # FIXME(machenbach): Add back simdjs_small once download is fixed.
        'tests': ['unittests', 'v8testing', 'webkit'],
        'testing': {'platform': 'win'},
      },
      'v8_mac_rel': {
        'chromium_apply_config': ['v8_ninja', 'clang', 'goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'webkit', 'simdjs_small'],
        'testing': {'platform': 'mac'},
      },
      'v8_mac_dbg': {
        'chromium_apply_config': ['v8_ninja', 'clang', 'goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'webkit', 'simdjs_small'],
        'testing': {'platform': 'mac'},
      },
      'v8_mac64_rel': {
        'chromium_apply_config': ['v8_ninja', 'clang', 'goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'webkit', 'simdjs_small'],
        'testing': {'platform': 'mac'},
      },
      'v8_mac64_dbg': {
        'chromium_apply_config': ['v8_ninja', 'clang', 'goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'webkit', 'simdjs_small'],
        'testing': {'platform': 'mac'},
      },
      'v8_mac64_asan_rel': {
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'asan',
          'goma',
          'no_dcheck',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing'],
        'testing': {'platform': 'mac'},
      },
      'v8_linux_arm_rel': {
        'chromium_apply_config': ['simulate_arm', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'webkit', 'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_arm_dbg': {
        'chromium_apply_config': ['simulate_arm', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'webkit', 'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_arm64_rel': {
        'chromium_apply_config': ['simulate_arm', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'webkit', 'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_arm64_dbg': {
        'chromium_apply_config': ['simulate_arm', 'v8_goma'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['unittests', 'v8testing', 'webkit', 'simdjs_small'],
        'testing': {'platform': 'linux'},
      },
      'v8_android_arm_compile_rel': {
        'gclient_apply_config': ['android'],
        'chromium_apply_config': [
          'v8_ninja',
          'default_compiler',
          'goma',
          'no_dcheck',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
          'TARGET_PLATFORM': 'android',
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'v8_linux_mipsel_compile_rel': {
        'chromium_apply_config': ['simulate_mipsel', 'v8_goma', 'no_dcheck'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'v8_linux_mips64el_compile_rel': {
        'chromium_apply_config': ['simulate_mipsel', 'v8_goma', 'no_dcheck'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
    },
  },
####### Waterfall: client.dynamorio
  'client.dynamorio': {
    'builders': {
      'linux-v8-dr': {
        'gclient_apply_config': ['dynamorio'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': ['v8testing'],
        'testing': {'platform': 'linux'},
      },
    },
  },
}

####### Waterfall: client.v8.branches
BRANCH_BUILDERS = {}

def AddBranchBuilder(build_config, arch, bits, presubmit=False,
                     unittests_only=False):
  tests = ['unittests']
  if not unittests_only:
    tests += ['v8testing', 'webkit', 'test262', 'mozilla']
  if presubmit:
    tests = ['presubmit'] + tests
  return {
    'chromium_apply_config': ['v8_goma'],
    'v8_config_kwargs': {
      'BUILD_CONFIG': build_config,
      'TARGET_ARCH': arch,
      'TARGET_BITS': bits,
    },
    'bot_type': 'builder_tester',
    'tests': tests,
    'testing': {'platform': 'linux'},
  }

for build_config, name_suffix in (('Release', ''), ('Debug', ' - debug')):
  for branch_name in ('stable branch', 'beta branch', 'roll branch'):
    name = 'V8 Linux - %s%s' % (branch_name, name_suffix)
    BRANCH_BUILDERS[name] = AddBranchBuilder(
        build_config, 'intel', 32, presubmit=True)
    name = 'V8 Linux64 - %s%s' % (branch_name, name_suffix)
    BRANCH_BUILDERS[name] = AddBranchBuilder(build_config, 'intel', 64)
    name = 'V8 arm - sim - %s%s' % (branch_name, name_suffix)
    BRANCH_BUILDERS[name] = AddBranchBuilder(build_config, 'intel', 32)
    BRANCH_BUILDERS[name]['chromium_apply_config'].append('simulate_arm')

for branch_name in ('stable branch', 'beta branch'):
  name = 'V8 mipsel - sim - %s' % branch_name
  BRANCH_BUILDERS[name] = AddBranchBuilder(
      'Release', 'intel', 32, unittests_only=True)
  BRANCH_BUILDERS[name]['chromium_apply_config'].append('simulate_mipsel')

  name = 'V8 mips64el - sim - %s' % branch_name
  BRANCH_BUILDERS[name] = AddBranchBuilder(
      'Release', 'intel', 64, unittests_only=True)
  BRANCH_BUILDERS[name]['chromium_apply_config'].append('simulate_mipsel')

  name = 'V8 ppc - sim - %s' % branch_name
  BRANCH_BUILDERS[name] = AddBranchBuilder(
      'Release', 'intel', 32, unittests_only=True)
  BRANCH_BUILDERS[name]['chromium_apply_config'].append('simulate_ppc')

  name = 'V8 ppc64 - sim - %s' % branch_name
  BRANCH_BUILDERS[name] = AddBranchBuilder(
      'Release', 'intel', 64, unittests_only=True)
  BRANCH_BUILDERS[name]['chromium_apply_config'].append('simulate_ppc')

BUILDERS['client.v8.branches'] = {'builders': BRANCH_BUILDERS}

BUILDERS['client.dart.fyi'] = {'builders': {
  'v8-%s-release' % platform: {
    'chromium_apply_config': ['disassembler'],
    'v8_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_ARCH': 'intel',
      'TARGET_BITS': 32,
    },
    'bot_type': 'builder',
    'build_gs_archive': 'v8_for_dart_archive',
    'testing': {'platform': platform},
  } for platform in ('win', 'linux', 'mac')
}}

dart_linux_release = (
  BUILDERS['client.dart.fyi']['builders']['v8-linux-release'])
dart_linux_release['chromium_apply_config'].extend(['v8_goma'])

dart_mac_release = BUILDERS['client.dart.fyi']['builders']['v8-mac-release']
dart_mac_release['chromium_apply_config'].extend(['v8_ninja', 'clang', 'goma'])

dart_win_release = BUILDERS['client.dart.fyi']['builders']['v8-win-release']
dart_win_release['chromium_apply_config'].extend(['v8_ninja', 'msvs2013'])

BUILDERS = freeze(BUILDERS)
BRANCH_BUILDERS = freeze(BRANCH_BUILDERS)
