# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Contains the bulk of the V8 builder configurations so they can be reused
# from multiple recipes.

from recipe_engine.types import freeze
from testing import V8NoExhaustiveVariants, V8Variant, V8VariantNeutral


class TestStepConfig(object):
  """Per-step test configuration."""
  def __init__(self, name, shards=1, swarming=True, suffix='', test_args=None,
               variants=V8VariantNeutral):
    self.name = name
    self.shards = shards
    self.swarming = swarming
    self.suffix = ' - ' + suffix if suffix else ''
    self.test_args = test_args or []
    self.variants = variants

  def __call__(self, shards):
    return TestStepConfig(self.name, shards, self.swarming, self.suffix,
                          self.test_args, self.variants)


# Top-level test configs for convenience.
Benchmarks = TestStepConfig('benchmarks')
Deopt = TestStepConfig('deopt')
Fuzz = TestStepConfig('jsfunfuzz')
GCMole = TestStepConfig('gcmole')
Mjsunit = TestStepConfig('mjsunit')
MjsunitSPFrameAccess = TestStepConfig('mjsunit_sp_frame_access')
Mozilla = TestStepConfig('mozilla')
OptimizeForSize = TestStepConfig('optimize_for_size')
Presubmit = TestStepConfig('presubmit')
Test262 = TestStepConfig('test262')
Test262Variants = TestStepConfig('test262_variants')
Unittests = TestStepConfig('unittests')
V8Initializers = TestStepConfig('v8initializers')
V8Testing = TestStepConfig('v8testing')
Webkit = TestStepConfig('webkit')


def with_test_args(suffix, test_args, tests, variants=V8VariantNeutral):
  """Wrapper that runs a list of tests with additional arguments."""
  return [
    TestStepConfig(t.name, t.shards, t.swarming, suffix, test_args, variants)
    for t in tests
  ]


SWARMING_FYI_PROPS = {
  'default_expiration': 2 * 60 * 60,
  'default_hard_timeout': 60 * 60,
  'default_priority': 35,
}

BUILDERS = {
####### Waterfall: client.v8
  'client.v8': {
    'builders': {
####### Category: Linux
      'V8 Linux - builder': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'gcmole', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux_rel_archive',
        'enable_swarming': True,
        'testing': {
          'platform': 'linux',
        },
        'binary_size_tracking': {
          'path_pieces_list': [['d8']],
          'category': 'linux32'
        },
        'triggers': [
          'V8 Linux',
          'V8 Linux - presubmit',
        ],
        'triggers_proxy': True,
      },
      'V8 Linux - debug builder': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux_dbg_archive',
        'enable_swarming': True,
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Linux - gc stress',
          'V8 Linux - debug',
          'V8 Linux - debug - avx2',
        ],
      },
      'V8 Linux - nosnap builder': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'no_snapshot', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux_nosnap_rel_archive',
        'enable_swarming': True,
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Linux - nosnap',
        ],
      },
      'V8 Linux - nosnap debug builder': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'no_snapshot', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux_nosnap_dbg_archive',
        'enable_swarming': True,
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Linux - nosnap - debug',
        ],
      },
      'V8 Linux - presubmit': {
        'chromium_apply_config': ['gn'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - builder',
        'build_gs_archive': 'linux_rel_archive',
        'tests': [Presubmit],
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
          V8Initializers,
          V8Testing,
          OptimizeForSize,
          Benchmarks,
          Test262Variants(2),
          Mozilla,
          MjsunitSPFrameAccess,
          GCMole,
        ] + with_test_args(
            'isolates',
            ['--isolates'],
            [V8Testing],
        ) + with_test_args(
            'nosse3',
            ['--extra-flags', '--noenable-sse3 --noenable-avx'],
            [V8Testing, Mozilla],
        ) + with_test_args(
            'nosse4',
            ['--extra-flags', '--noenable-sse4-1 --noenable-avx'],
            [V8Testing, Mozilla],
        ),
        'testing': {'platform': 'linux'},
        'enable_swarming': True,
      },
      'V8 Linux - debug': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'enable_swarming': True,
        'tests': [
          V8Testing(2),
          Benchmarks,
          Test262Variants(4),
          Mozilla,
          MjsunitSPFrameAccess,
        ] + with_test_args(
            'isolates',
            ['--isolates'],
            [V8Testing(2)],
        ) + with_test_args(
            'nosse3',
            ['--extra-flags', '--noenable-sse3 --noenable-avx'],
            [V8Testing(2), Test262, Mozilla],
        ) + with_test_args(
            'nosse4',
            ['--extra-flags', '--noenable-sse4-1 --noenable-avx'],
            [V8Testing(2), Test262, Mozilla],
        ) + with_test_args(
            'code serializer',
            ['--extra-flags', '--serialize-toplevel --cache=code'],
            [Mjsunit, Mozilla, Test262, Benchmarks],
            V8Variant('default'),
        ),
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - debug - avx2': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'enable_swarming': True,
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'tests': [V8Testing, Benchmarks, Mozilla],
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'cpu': 'x86-64-avx2',
        },
      },
      'V8 Linux - shared': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'shared_library',
          'verify_heap', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [V8Testing, Test262, Mozilla],
        'testing': {'platform': 'linux'},
        'binary_size_tracking': {
          'path_pieces_list': [['libv8.so']],
          'category': 'linux32'
        },
      },
      'V8 Linux - nosnap': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - nosnap builder',
        'build_gs_archive': 'linux_nosnap_rel_archive',
        'enable_swarming': True,
        'tests': [
          V8Testing(3),
          Test262(2),
          Mozilla,
        ],
        'variants': V8NoExhaustiveVariants(),
        'testing': {'platform': 'linux'},
        'swarming_properties': SWARMING_FYI_PROPS,
      },
      'V8 Linux - nosnap - debug': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - nosnap debug builder',
        'build_gs_archive': 'linux_nosnap_dbg_archive',
        'enable_swarming': True,
        'tests': [V8Testing(7)],
        'variants': V8NoExhaustiveVariants(),
        'testing': {'platform': 'linux'},
        'swarming_properties': SWARMING_FYI_PROPS,
      },
      'V8 Linux - interpreted regexp': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'interpreted_regexp', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
        'swarming_properties': SWARMING_FYI_PROPS,
      },
      'V8 Linux - noi18n - debug': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'no_i18n', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [V8Testing, Mozilla, Test262],
        'variants': V8NoExhaustiveVariants(),
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - verify csa': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
      },
####### Category: Linux64
      'V8 Linux64 - builder': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux64_rel_archive',
        'enable_swarming': True,
        'testing': {'platform': 'linux'},
        'track_build_dependencies': True,
        'binary_size_tracking': {
          'path_pieces_list': [['d8']],
          'category': 'linux64'
        },
        'triggers': [
          'V8 Linux64',
          'V8 Linux64 - avx2',
        ],
        'triggers_proxy': True,
      },
      'V8 Linux64 - concurrent marking - builder': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux64_rel_cm_archive',
        'testing': {'platform': 'linux'},
        'triggers_proxy': True,
      },
      'V8 Linux64 - debug builder': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'jsfunfuzz', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux64_dbg_archive',
        'testing': {'platform': 'linux'},
        'enable_swarming': True,
        'triggers': [
          'V8 Fuzzer',
          'V8 Linux64 - debug',
          'V8 Linux64 - debug - avx2',
        ],
      },
      'V8 Linux64 - custom snapshot - debug builder': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'embed_script_mjsunit',
          'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux64_custom_snapshot_dbg_archive',
        'testing': {'platform': 'linux'},
        'enable_swarming': True,
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
        'enable_swarming': True,
        'tests': [
          V8Initializers,
          V8Testing,
          OptimizeForSize,
          Test262Variants(2),
          Mozilla,
          MjsunitSPFrameAccess,
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
        'enable_swarming': True,
        'tests': [
          V8Testing,
          Benchmarks,
          Mozilla,
        ],
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'cpu': 'x86-64-avx2',
        },
      },
      'V8 Linux64 - debug': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux64 - debug builder',
        'build_gs_archive': 'linux64_dbg_archive',
        'enable_swarming': True,
        'tests': [
          V8Testing(2),
          OptimizeForSize,
          Test262Variants(5),
          Mozilla,
          MjsunitSPFrameAccess,
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
        'enable_swarming': True,
        'tests': [
          V8Testing(2),
          Benchmarks,
          Mozilla,
        ],
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'cpu': 'x86-64-avx2',
        },
      },
      'V8 Linux64 - internal snapshot': {
        'chromium_apply_config': [
          'v8_ninja', 'default_compiler', 'goma', 'internal_snapshot', 'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 - custom snapshot - debug': {
        'v8_apply_config': ['no_harness'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'enable_swarming': True,
        'parent_buildername': 'V8 Linux64 - custom snapshot - debug builder',
        'build_gs_archive': 'linux64_custom_snapshot_dbg_archive',
        'tests': [Mjsunit],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 - gyp': {
        'chromium_apply_config': [
          'v8_ninja', 'default_compiler', 'goma', 'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 - verify csa': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
      },
####### Category: Windows
      'V8 Win32 - builder': {
        'chromium_apply_config': [
          'default_compiler',
          'v8_ninja',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'win32_rel_archive',
        'enable_swarming': True,
        'binary_size_tracking': {
          'path_pieces_list': [['d8.exe']],
          'category': 'win32'
        },
        'testing': {'platform': 'win'},
        'triggers': [
          'V8 Win32',
        ],
      },
      'V8 Win32 - debug builder': {
        'chromium_apply_config': [
          'default_compiler',
          'v8_ninja',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'win32_dbg_archive',
        'enable_swarming': True,
        'testing': {'platform': 'win'},
        'triggers': [
          'V8 Win32 - debug',
        ],
      },
      'V8 Win32': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'build_gs_archive': 'win32_rel_archive',
        'parent_buildername': 'V8 Win32 - builder',
        'enable_swarming': True,
        'tests': [V8Testing, Test262, Mozilla],
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86-64',
        },
      },
      'V8 Win32 - nosnap - shared': {
        'chromium_apply_config': [
          'default_compiler',
          'v8_ninja',
          'goma',
          'shared_library',
          'no_snapshot',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [V8Testing(2)],
        'variants': V8NoExhaustiveVariants(),
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86-64',
        },
        'testing': {'platform': 'win'},
      },
      'V8 Win32 - debug': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'build_gs_archive': 'win32_dbg_archive',
        'parent_buildername': 'V8 Win32 - debug builder',
        'enable_swarming': True,
        'tests': [
          V8Testing(3),
          Test262,
          Mozilla,
        ],
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86-64',
        },
      },
      'V8 Win64': {
        'chromium_apply_config': [
          'default_compiler',
          'v8_ninja',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
        },
        'binary_size_tracking': {
          'path_pieces_list': [['d8.exe']],
          'category': 'win64'
        },
        'tests': [
          V8Testing,
          Test262,
          Mozilla,
        ],
        'testing': {'platform': 'win'},
      },
      'V8 Win64 - debug': {
        'chromium_apply_config': [
          'default_compiler',
          'v8_ninja',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
        },
        'tests': [
          V8Testing(3),
          Test262,
          Mozilla,
        ],
        'testing': {'platform': 'win'},
      },
      'V8 Win64 - clang': {
        'chromium_apply_config': [
          'clang',
          'v8_ninja',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
####### Category: Mac
      'V8 Mac': {
        'chromium_apply_config': [
          'v8_ninja', 'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'binary_size_tracking': {
          'path_pieces_list': [['d8']],
          'category': 'mac32'
        },
        'tests': [
          V8Testing,
          Test262,
          Mozilla,
        ],
        'swarming_dimensions': {
          'os': 'Mac-10.9',
          'cpu': 'x86-64',
        },
        'testing': {'platform': 'mac'},
      },
      'V8 Mac - debug': {
        'chromium_apply_config': [
          'v8_ninja', 'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [
          V8Testing(3),
          Test262,
          Mozilla,
        ],
        'swarming_dimensions': {
          'os': 'Mac-10.9',
          'cpu': 'x86-64',
        },
        'testing': {'platform': 'mac'},
      },
      'V8 Mac64': {
        'chromium_apply_config': [
          'v8_ninja', 'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'binary_size_tracking': {
          'path_pieces_list': [['d8']],
          'category': 'mac64'
        },
        'tests': [
          V8Testing,
          Test262,
          Mozilla,
        ],
        'swarming_dimensions': {
          'os': 'Mac-10.9',
          'cpu': 'x86-64',
        },
        'testing': {'platform': 'mac'},
      },
      'V8 Mac64 - debug': {
        'chromium_apply_config': [
          'v8_ninja', 'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [
          V8Testing(3),
          Test262,
          Mozilla,
        ],
        'swarming_dimensions': {
          'os': 'Mac-10.9',
          'cpu': 'x86-64',
        },
        'testing': {'platform': 'mac'},
      },
####### Category: Misc
      'V8 Fuzzer': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'enable_swarming': True,
        'parent_buildername': 'V8 Linux64 - debug builder',
        'build_gs_archive': 'linux64_dbg_archive',
        'tests': [Fuzz],
        'testing': {'platform': 'linux'},
        'swarming_properties': SWARMING_FYI_PROPS,
      },
      'V8 Linux - gc stress': {
        'v8_apply_config': ['gc_stress'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - debug builder',
        'build_gs_archive': 'linux_dbg_archive',
        'enable_swarming': True,
        'tests': [Mjsunit(4), Webkit],
        'testing': {'platform': 'linux'},
      },
      'V8 Mac GC Stress': {
        'chromium_apply_config': [
          'v8_ninja', 'default_compiler', 'goma', 'mb'],
        'v8_apply_config': ['gc_stress'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [Mjsunit(3), Webkit],
        'swarming_dimensions': {
          'os': 'Mac-10.9',
          'cpu': 'x86-64',
        },
        'testing': {'platform': 'mac'},
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
        'enable_swarming': True,
        'tests': [Mjsunit(3)],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux gcc 4.8': {
        'chromium_apply_config': ['v8_ninja', 'gcc', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 gcc 4.8 - debug': {
        'chromium_apply_config': ['v8_ninja', 'gcc', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 ASAN': {
        'chromium_apply_config': ['v8_ninja', 'clang', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [
          V8Testing(2),
          Test262Variants(3),
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 TSAN': {
        'chromium_apply_config': ['v8_ninja', 'clang', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [
          V8Testing(3),
          Test262(2),
          Mozilla,
          Benchmarks,
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 TSAN - concurrent marking': {
        'chromium_apply_config': ['v8_ninja', 'clang', 'goma', 'mb'],
        'v8_apply_config': ['stress_incremental_marking'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [
          V8Testing(2),
          Test262(4),
          Mozilla,
          Benchmarks,
        ],
        'testing': {'platform': 'linux'},
        'swarming_properties': SWARMING_FYI_PROPS,
      },
      'V8 Linux - arm64 - sim - MSAN': {
        'gclient_apply_config': ['checkout_instrumented_libraries'],
        # 'simulate_arm' is actually implied by 'msan'. We still set it
        # explicitly for the sake of consistency.
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'simulate_arm',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [
          V8Testing(4),
          Test262(2),
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 - cfi': {
        'chromium_apply_config': [
          'v8_ninja', 'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [
          V8Testing,
          OptimizeForSize,
          Benchmarks,
          Test262,
          Mozilla,
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 UBSanVptr': {
        'chromium_apply_config': [
          'v8_ninja', 'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
      },
      'V8 Mac64 ASAN': {
        'chromium_apply_config': ['v8_ninja', 'clang', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [V8Testing(5)],
        'swarming_dimensions': {
          'os': 'Mac-10.9',
          'cpu': 'x86-64',
        },
        'testing': {'platform': 'mac'},
      },
      'V8 Win32 ASAN': {
        'chromium_apply_config': ['v8_ninja', 'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [V8Testing(5)],
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
        },
        'testing': {'platform': 'win'},
      },
####### Category: FYI
      'V8 Fuchsia': {
        'gclient_apply_config': ['fuchsia'],
        'chromium_apply_config': ['default_compiler', 'v8_ninja', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'testing': {'platform': 'linux'},
      },
      'V8 Fuchsia - debug': {
        'gclient_apply_config': ['fuchsia'],
        'chromium_apply_config': ['default_compiler', 'v8_ninja', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 - gcov coverage': {
        'chromium_apply_config': [
          'clobber', 'v8_ninja', 'gcc', 'coverage', 'goma', 'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'gcov_coverage_folder': 'linux64_gcov_rel',
        'disable_auto_bisect': True,
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - vtunejit': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'vtunejit', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - predictable': {
        'chromium_apply_config': [
          'v8_ninja', 'default_compiler', 'goma', 'predictable', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [Mjsunit, Webkit, Benchmarks, Mozilla],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - full debug': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'no_optimized_debug', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [V8Testing],
        'variants': V8NoExhaustiveVariants(),
        'testing': {'platform': 'linux'},
      },
    },
  },
####### Waterfall: client.v8.clusterfuzz
  'client.v8.clusterfuzz': {
    'builders': {
      'V8 Linux64 - release builder': {
        'chromium_apply_config': [
          'clang',
          'v8_ninja',
          'goma',
          'mb',
          'default_target_v8_clusterfuzz',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'slim_swarming_builder': True,
        'enable_swarming': True,
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-asan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8',
        'triggers': [
          'V8 Deopt Fuzzer',
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 - debug builder': {
        'chromium_apply_config': [
          'clang',
          'v8_ninja',
          'goma',
          'mb',
          'default_target_v8_clusterfuzz',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'slim_swarming_builder': True,
        'enable_swarming': True,
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-asan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8',
        'triggers': [
          'V8 Random Deopt Fuzzer - debug',
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 ASAN no inline - release builder': {
        'chromium_apply_config': [
          'clang',
          'v8_ninja',
          'goma',
          'mb',
          'clobber',
          'default_target_v8_clusterfuzz',
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
          'default_target_v8_clusterfuzz',
          'goma',
          'mb',
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
          'default_target_v8_clusterfuzz',
          'goma',
          'mb',
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
          'default_target_v8_clusterfuzz',
          'goma',
          'mb',
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
          'default_target_v8_clusterfuzz',
          'goma',
          'mb',
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
      'V8 Linux64 CFI - release builder': {
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'default_target_v8_clusterfuzz',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-cfi',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8-cfi',
        'testing': {'platform': 'linux'},
      },
      'V8 Linux MSAN no origins': {
        'gclient_apply_config': ['checkout_instrumented_libraries'],
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'default_target_v8_clusterfuzz',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-msan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8-msan-no-origins',
        'testing': {'platform': 'linux'},
      },
      'V8 Linux MSAN chained origins': {
        'gclient_apply_config': ['checkout_instrumented_libraries'],
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'default_target_v8_clusterfuzz',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-msan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8-msan-chained-origins',
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 UBSan - release builder': {
        'chromium_apply_config': [
          'v8_ninja',
          'default_compiler',
          'goma',
          'default_target_v8_clusterfuzz',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-ubsan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8-ubsan',
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 UBSanVptr - release builder': {
        'chromium_apply_config': [
          'v8_ninja',
          'default_compiler',
          'goma',
          'default_target_v8_clusterfuzz',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-ubsan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8-ubsan-vptr',
        'testing': {'platform': 'linux'},
      },
      'V8 Mac64 ASAN - release builder': {
        'chromium_apply_config': [
          'v8_ninja',
          'default_compiler',
          'goma',
          'default_target_v8_clusterfuzz',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'cf_archive_build': True,
        'cf_gs_bucket': 'v8-asan',
        'cf_gs_acl': 'public-read',
        'cf_archive_name': 'd8-asan',
        'testing': {'platform': 'mac'},
      },
      'V8 Mac64 ASAN - debug builder': {
        'chromium_apply_config': [
          'v8_ninja',
          'default_compiler',
          'goma',
          'default_target_v8_clusterfuzz',
          'mb',
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
        'testing': {'platform': 'mac'},
      },
      'V8 Deopt Fuzzer': {
        'v8_apply_config': ['deopt_fuzz_normal'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'enable_swarming': True,
        'parent_buildername': 'V8 Linux64 - release builder',
        'tests': [Deopt],
        'variants': V8NoExhaustiveVariants(),
        'testing': {'platform': 'linux'},
        'swarming_properties': SWARMING_FYI_PROPS,
      },
      'V8 Random Deopt Fuzzer - debug': {
        'v8_apply_config': ['deopt_fuzz_random'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'enable_swarming': True,
        'parent_buildername': 'V8 Linux64 - debug builder',
        'tests': [Deopt],
        'variants': V8NoExhaustiveVariants(),
        'testing': {'platform': 'linux'},
        'swarming_properties': {
          'default_expiration': 2 * 60 * 60,
          'default_hard_timeout': 2 * 60 * 60,
          'default_priority': 35,
        },
      },
    },
  },
####### Waterfall: client.v8.ports
  'client.v8.ports': {
    'builders': {
####### Category: Arm
      'V8 Arm - builder': {
        'chromium_apply_config': [
            'v8_ninja', 'default_compiler', 'goma', 'arm_hard_float', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'arm_rel_archive',
        'enable_swarming': True,
        'binary_size_tracking': {
          'path_pieces_list': [['d8']],
          'category': 'linux_arm32'
        },
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Arm',
        ],
        'triggers_proxy': True,
      },
      'V8 Arm - debug builder': {
        'chromium_apply_config': [
            'v8_ninja', 'default_compiler', 'goma', 'arm_hard_float', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'arm_dbg_archive',
        'enable_swarming': True,
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Arm - debug',
          'V8 Arm GC Stress',
        ],
      },
      'V8 Android Arm - builder': {
        'gclient_apply_config': ['android'],
        'chromium_apply_config': [
          'v8_ninja', 'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
          'TARGET_PLATFORM': 'android',
        },
        'bot_type': 'builder',
        'build_gs_archive': 'android_arm_rel_archive',
        'enable_swarming': True,
        'binary_size_tracking': {
          'path_pieces_list': [['d8']],
          'category': 'android_arm32'
        },
        'testing': {'platform': 'linux'},
        'triggers_proxy': True,
      },
      'V8 Arm': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'build_gs_archive': 'arm_rel_archive',
        'parent_buildername': 'V8 Arm - builder',
        'tests': [
          V8Testing(2),
          Benchmarks,
          OptimizeForSize,
        ],
        'enable_swarming': True,
        'swarming_properties': {
          'default_hard_timeout': 90 * 60,
          'default_expiration': 6 * 60 * 60,
        },
        'swarming_dimensions': {
          'cpu': 'armv7l',
          'cores': '2',
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Arm - debug': {
        'v8_apply_config': ['verify_heap_skip_remembered_set'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'build_gs_archive': 'arm_dbg_archive',
        'parent_buildername': 'V8 Arm - debug builder',
        'tests': [
          V8Testing(3),
          OptimizeForSize,
        ],
        'variants': V8NoExhaustiveVariants(),
        'enable_swarming': True,
        'swarming_properties': {
          'default_hard_timeout': 60 * 60,
          'default_expiration': 6 * 60 * 60,
        },
        'swarming_dimensions': {
          'cpu': 'armv7l',
          'cores': '2',
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Arm GC Stress': {
        'v8_apply_config': ['gc_stress', 'verify_heap_skip_remembered_set'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'build_gs_archive': 'arm_dbg_archive',
        'parent_buildername': 'V8 Arm - debug builder',
        'tests': [Mjsunit(2), Webkit],
        'variants': V8Variant('default'),
        'enable_swarming': True,
        'swarming_properties': {
          'default_hard_timeout': 2 * 60 * 60,
          'default_expiration': 6 * 60 * 60,
        },
        'swarming_dimensions': {
          'cpu': 'armv7l',
          'cores': '2',
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm - sim': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_arm', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [
          V8Testing(4),
          Test262,
          Mozilla,
          MjsunitSPFrameAccess,
        ] + with_test_args(
            'armv8-a',
            ['--extra-flags', '--enable-armv8'],
            [V8Testing(4), Test262, Mozilla],
        ) + with_test_args(
            'novfp3',
            ['--novfp3'],
            [V8Testing(4), Test262, Mozilla],
        ),
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm - sim - debug': {
        'chromium_apply_config': ['default_compiler', 'v8_ninja', 'goma', 'simulate_arm', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [
          V8Testing(4),
          Test262,
          Mozilla,
          MjsunitSPFrameAccess,
        ] + with_test_args(
            'armv8-a',
            ['--extra-flags', '--enable-armv8'],
            [V8Testing(4), Test262, Mozilla],
        ) + with_test_args(
            'novfp3',
            ['--novfp3'],
            [V8Testing(4), Test262, Mozilla],
            V8NoExhaustiveVariants(),
        ),
        'testing': {'platform': 'linux'},
      },
####### Category: ARM64
      'V8 Android Arm64 - builder': {
        'gclient_apply_config': ['android'],
        'chromium_apply_config': [
          'v8_ninja', 'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
          'TARGET_PLATFORM': 'android',
        },
        'bot_type': 'builder',
        'build_gs_archive': 'android_arm64_rel_archive',
        'enable_swarming': True,
        'binary_size_tracking': {
          'path_pieces_list': [['d8']],
          'category': 'android_arm64'
        },
        'testing': {'platform': 'linux'},
        'triggers_proxy': True,
      },
      'V8 Linux - arm64 - sim': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_arm', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [
          V8Testing(3),
          Test262,
          Mozilla,
          MjsunitSPFrameAccess,
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm64 - sim - debug': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_arm', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [
          V8Testing(4),
          Test262,
          Mozilla,
          MjsunitSPFrameAccess,
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm64 - sim - nosnap - debug': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_arm',
          'no_snapshot', 'mb'],
        'v8_apply_config': ['verify_heap_skip_remembered_set'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [V8Testing(7)],
        'variants': V8Variant('default'),
        'testing': {'platform': 'linux'},
        'swarming_properties': {
          'default_expiration': 2 * 60 * 60,
          'default_hard_timeout': 2 * 60 * 60,
          'default_priority': 35,
        },
      },
      'V8 Linux - arm64 - sim - gc stress': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_arm', 'mb'],
        'v8_apply_config': ['gc_stress', 'verify_heap_skip_remembered_set'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'swarming_properties': {
          'default_expiration': 2 * 60 * 60,
          'default_hard_timeout': 2 * 60 * 60,
          'default_priority': 35,
        },
        'tests': [Mjsunit(4), Webkit],
        'testing': {'platform': 'linux'},
      },
####### Category: MIPS
      'V8 Mips - builder': {
        # TODO(machenbach): Switch this bot manually to gn.
        'chromium_apply_config': ['no_snapshot', 'no_i18n'],
        'v8_apply_config': ['mips_cross_compile'],
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
        'tests': [V8Testing],
        'variants': V8NoExhaustiveVariants(),
        'testing': {'platform': 'linux'},
      },
      'V8 Mips - big endian - nosnap - 2': {
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
        'tests': [V8Testing],
        'variants': V8NoExhaustiveVariants(),
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - mipsel - sim - builder': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_mipsel', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'mipsel_sim_rel_archive',
        'enable_swarming': True,
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Linux - mipsel - sim',
        ],
      },
      'V8 Linux - mips64el - sim - builder': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_mipsel', 'mb'],
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
        'enable_swarming': True,
        'tests': [V8Testing(4), Test262],
        'testing': {'platform': 'linux'},
        'swarming_properties': {
          'default_expiration': 2 * 60 * 60,
          'default_hard_timeout': 2 * 60 * 60,
          'default_priority': 35,
        },
      },
####### Category: PPC
      'V8 Linux - ppc - sim': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_ppc', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [V8Testing(3)],
        'testing': {'platform': 'linux'},
        'swarming_properties': SWARMING_FYI_PROPS,
      },
      'V8 Linux - ppc64 - sim': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_ppc', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [V8Testing(3)],
        'testing': {'platform': 'linux'},
        'swarming_properties': SWARMING_FYI_PROPS,
      },
####### Category: S390
      'V8 Linux - s390 - sim': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_s390', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [V8Testing(3)],
        'testing': {'platform': 'linux'},
        'swarming_properties': SWARMING_FYI_PROPS,
      },
      'V8 Linux - s390x - sim': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_s390', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [V8Testing(3)],
        'testing': {'platform': 'linux'},
        'swarming_properties': SWARMING_FYI_PROPS,
      },
    },
  },
####### Waterfall: client.v8.official
  'client.v8.official': {
    'builders': {
      'V8 Android Arm32': {
        'recipe': 'v8/archive',
        'gclient_apply_config': ['android'],
        'chromium_apply_config': [
          'clobber', 'default_compiler', 'default_target_v8_archive',
          'v8_android', 'v8_static_library', 'v8_ninja', 'goma', 'gn'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
          'TARGET_PLATFORM': 'android',
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Android Arm64': {
        'recipe': 'v8/archive',
        'gclient_apply_config': ['android'],
        'chromium_apply_config': [
          'clobber', 'default_compiler', 'default_target_v8_archive',
          'v8_android', 'v8_static_library', 'v8_ninja', 'goma', 'gn'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
          'TARGET_PLATFORM': 'android',
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Linux32': {
        'recipe': 'v8/archive',
        'chromium_apply_config': [
          'clobber', 'default_compiler', 'default_target_v8_archive',
          'v8_static_library', 'v8_ninja', 'goma', 'gn'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64': {
        'recipe': 'v8/archive',
        'chromium_apply_config': [
          'clobber', 'default_compiler', 'default_target_v8_archive',
          'v8_static_library', 'v8_ninja', 'goma', 'gn'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'testing': {'platform': 'linux'},
      },
    },
  },
####### Waterfall: tryserver.v8
  'tryserver.v8': {
    'builders': {
      'v8_fuchsia_rel_ng': {
        'gclient_apply_config': ['fuchsia'],
        'chromium_apply_config': ['default_compiler', 'v8_ninja', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'v8_linux_rel_ng': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'gcmole', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'enable_swarming': True,
        'slim_swarming_builder': True,
        'triggers': [
          'v8_linux_rel_ng_triggered',
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_rel_ng_triggered': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'v8_linux_rel_ng',
        'enable_swarming': True,
        'tests': [
          V8Testing,
          OptimizeForSize,
          Test262Variants(4),
          Mozilla,
          Benchmarks,
          MjsunitSPFrameAccess,
          GCMole,
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_verify_csa_rel_ng': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'enable_swarming': True,
        'slim_swarming_builder': True,
        'triggers': [
          'v8_linux_verify_csa_rel_ng_triggered',
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_verify_csa_rel_ng_triggered': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'v8_linux_verify_csa_rel_ng',
        'enable_swarming': True,
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_avx2_dbg': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [
          V8Testing(2),
        ],
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'cpu': 'x86-64-avx2',
        },
      },
      'v8_linux_nodcheck_rel_ng': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'no_dcheck', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'enable_swarming': True,
        'slim_swarming_builder': True,
        'triggers': [
          'v8_linux_nodcheck_rel_ng_triggered',
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_nodcheck_rel_ng_triggered': {
        'chromium_apply_config': ['no_dcheck'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'v8_linux_nodcheck_rel_ng',
        'enable_swarming': True,
        'tests': [
          V8Testing,
          Test262Variants(2),
          Mozilla,
          Benchmarks,
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_dbg_ng': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'enable_swarming': True,
        'slim_swarming_builder': True,
        'triggers': [
          'v8_linux_dbg_ng_triggered',
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_dbg_ng_triggered': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'v8_linux_dbg_ng',
        'enable_swarming': True,
        'tests': [
          V8Testing(3),
          Test262,
          Mozilla,
          Benchmarks,
          MjsunitSPFrameAccess,
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_noi18n_rel_ng': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'no_i18n', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'enable_swarming': True,
        'slim_swarming_builder': True,
        'triggers': [
          'v8_linux_noi18n_rel_ng_triggered',
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_noi18n_rel_ng_triggered': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'v8_linux_noi18n_rel_ng',
        'enable_swarming': True,
        'tests': [
          V8Testing(2),
          Test262,
          Mozilla,
        ],
        'variants': V8NoExhaustiveVariants(),
        'testing': {'platform': 'linux'},
      },
      'v8_linux_nosnap_rel': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'no_snapshot', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [V8Testing(4)],
        'variants': V8NoExhaustiveVariants(),
        'testing': {'platform': 'linux'},
      },
      'v8_linux_nosnap_dbg': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'no_snapshot', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [V8Testing(5)],
        'variants': V8NoExhaustiveVariants(),
        'testing': {'platform': 'linux'},
        'swarming_properties': {
          'default_hard_timeout': 60 * 60,
        },
      },
      'v8_linux_gcc_compile_rel': {
        'chromium_apply_config': [
          'v8_ninja', 'no_dcheck', 'gcc', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'v8_linux_gcc_rel': {
        'chromium_apply_config': [
          'v8_ninja', 'no_dcheck', 'gcc', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_shared_compile_rel': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_gcc_compile_dbg': {
        'chromium_apply_config': [
          'v8_ninja', 'gcc', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_rel_ng': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'enable_swarming': True,
        'slim_swarming_builder': True,
        'triggers': [
          'v8_linux64_rel_ng_triggered',
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_rel_ng_triggered': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'v8_linux64_rel_ng',
        'enable_swarming': True,
        'tests': [
          V8Initializers,
          V8Testing,
          OptimizeForSize,
          Test262Variants(4),
          MjsunitSPFrameAccess,
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_verify_csa_rel_ng': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'enable_swarming': True,
        'slim_swarming_builder': True,
        'triggers': [
          'v8_linux64_verify_csa_rel_ng_triggered',
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_verify_csa_rel_ng_triggered': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'v8_linux64_verify_csa_rel_ng',
        'enable_swarming': True,
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_gyp_rel_ng': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'no_dcheck', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'enable_swarming': True,
        'slim_swarming_builder': True,
        'triggers': [
          'v8_linux64_gyp_rel_ng_triggered',
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_gyp_rel_ng_triggered': {
        'chromium_apply_config': ['no_dcheck'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'v8_linux64_gyp_rel_ng',
        'enable_swarming': True,
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_avx2_rel_ng': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'enable_swarming': True,
        'slim_swarming_builder': True,
        'triggers': [
          'v8_linux64_avx2_rel_ng_triggered',
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_avx2_rel_ng_triggered': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'v8_linux64_avx2_rel_ng',
        'enable_swarming': True,
        'tests': [
          V8Testing,
        ],
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'cpu': 'x86-64-avx2',
        },
      },
      'v8_linux64_avx2_dbg': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [
          V8Testing(2),
        ],
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'cpu': 'x86-64-avx2',
        },
      },
      'v8_linux_gc_stress_dbg': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'mb'],
        'v8_apply_config': ['gc_stress'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [
          Mjsunit(4),
          Webkit,
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_asan_rel_ng': {
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'enable_swarming': True,
        'slim_swarming_builder': True,
        'triggers': [
          'v8_linux64_asan_rel_ng_triggered',
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_asan_rel_ng_triggered': {
        'chromium_apply_config': ['no_dcheck'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'v8_linux64_asan_rel_ng',
        'enable_swarming': True,
        'tests': [
          V8Testing(3),
          Test262Variants(7),
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_msan_rel': {
        'gclient_apply_config': ['checkout_instrumented_libraries'],
        # 'simulate_arm' is actually implied by 'msan'. We still set it
        # explicitly for the sake of consistency.
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'simulate_arm',
          'goma',
          'mb',
          'no_dcheck',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [
          V8Testing(5),
          Test262(2),
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_tsan_rel': {
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'goma',
          'mb',
          'no_dcheck',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [
          V8Testing(4),
          Test262(2),
          Mozilla,
          Benchmarks,
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_tsan_concurrent_marking_rel_ng': {
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'goma',
          'mb',
          'no_dcheck',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'slim_swarming_builder': True,
        'triggers': [
          'v8_linux64_tsan_concurrent_marking_rel_ng_triggered',
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_tsan_concurrent_marking_rel_ng_triggered': {
        'v8_apply_config': ['stress_incremental_marking'],
        'chromium_apply_config': ['no_dcheck'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'v8_linux64_tsan_concurrent_marking_rel_ng',
        'enable_swarming': True,
        'tests': [
          V8Testing(3),
          Test262(5),
          Mozilla,
          Benchmarks,
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_ubsan_rel_ng': {
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'enable_swarming': True,
        'slim_swarming_builder': True,
        'triggers': [
          'v8_linux64_ubsan_rel_ng_triggered',
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_ubsan_rel_ng_triggered': {
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'goma',
          'no_dcheck',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'v8_linux64_ubsan_rel_ng',
        'enable_swarming': True,
        'tests': [V8Testing(2)],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_sanitizer_coverage_rel': {
        'gclient_apply_config': ['llvm_compiler_rt'],
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'coverage',
          'goma',
          'mb',
          'no_dcheck',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'sanitizer_coverage_folder': 'linux64',
        'tests': [
          V8Testing(3),
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_win_asan_rel_ng': {
        'chromium_apply_config': [
          'default_compiler',
          'v8_ninja',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'enable_swarming': True,
        'slim_swarming_builder': True,
        'triggers': [
          'v8_win_asan_rel_ng_triggered',
        ],
        'testing': {'platform': 'win'},
      },
      'v8_win_asan_rel_ng_triggered': {
        'chromium_apply_config': [
          'use_windows_swarming_slaves',
          'no_dcheck',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'v8_win_asan_rel_ng',
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86-64',
        },
        'tests': [V8Testing(5)],
        'testing': {'platform': 'linux'},
      },
      'v8_win_dbg': {
        'chromium_apply_config': [
          'default_compiler',
          'v8_ninja',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86-64',
        },
        'tests': [
          V8Testing(3),
          Mozilla,
        ],
        'testing': {'platform': 'win'},
      },
      'v8_win_compile_dbg': {
        'chromium_apply_config': [
          'default_compiler',
          'v8_ninja',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'v8_win_rel_ng': {
        'chromium_apply_config': [
          'default_compiler',
          'v8_ninja',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'enable_swarming': True,
        'slim_swarming_builder': True,
        'triggers': [
          'v8_win_rel_ng_triggered',
        ],
        'testing': {'platform': 'win'},
      },
      'v8_win_rel_ng_triggered': {
        'chromium_apply_config': [
          'use_windows_swarming_slaves',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'v8_win_rel_ng',
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86-64',
        },
        'tests': [V8Testing, Test262],
        'testing': {'platform': 'linux'},
      },
      'v8_win_nosnap_shared_rel_ng': {
        'chromium_apply_config': [
          'default_compiler',
          'v8_ninja',
          'goma',
          'no_dcheck',
          'no_snapshot',
          'shared_library',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'enable_swarming': True,
        'slim_swarming_builder': True,
        'triggers': [
          'v8_win_nosnap_shared_rel_ng_triggered',
        ],
        'testing': {'platform': 'win'},
      },
      'v8_win_nosnap_shared_rel_ng_triggered': {
        'chromium_apply_config': [
          'no_dcheck',
          'use_windows_swarming_slaves',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'v8_win_nosnap_shared_rel_ng',
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86-64',
        },
        'tests': [V8Testing(3)],
        'variants': V8NoExhaustiveVariants(),
        'testing': {'platform': 'linux'},
      },
      'v8_win64_clang_compile_rel': {
        'chromium_apply_config': [
          'clang',
          'v8_ninja',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'v8_win64_rel_ng': {
        'chromium_apply_config': [
          'default_compiler',
          'v8_ninja',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'enable_swarming': True,
        'slim_swarming_builder': True,
        'triggers': [
          'v8_win64_rel_ng_triggered',
        ],
        'testing': {'platform': 'win'},
      },
      'v8_win64_rel_ng_triggered': {
        'chromium_apply_config': [
          'use_windows_swarming_slaves',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'v8_win64_rel_ng',
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86-64',
        },
        'tests': [V8Testing, Test262],
        'testing': {'platform': 'linux'},
      },
      'v8_win64_dbg': {
        'chromium_apply_config': [
          'default_compiler',
          'v8_ninja',
          'goma',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
        },
        'tests': [
          V8Testing(3),
          Test262(2),
          Mozilla,
        ],
        'testing': {'platform': 'win'},
      },
      'v8_mac_rel_ng': {
        'chromium_apply_config': [
          'v8_ninja', 'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'enable_swarming': True,
        'slim_swarming_builder': True,
        'triggers': [
          'v8_mac_rel_ng_triggered',
        ],
        'testing': {'platform': 'mac'},
      },
      'v8_mac_rel_ng_triggered': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'v8_mac_rel_ng',
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Mac-10.9',
          'cpu': 'x86-64',
        },
        'tests': [
          V8Testing,
          Test262,
          Mozilla,
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_mac_dbg': {
        'chromium_apply_config': [
          'v8_ninja', 'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [
          V8Testing(3),
          Test262,
          Mozilla,
        ],
        'swarming_dimensions': {
          'os': 'Mac-10.9',
          'cpu': 'x86-64',
        },
        'testing': {'platform': 'mac'},
      },
      'v8_mac64_rel': {
        'chromium_apply_config': [
          'v8_ninja', 'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [
          V8Testing,
          Test262,
          Mozilla,
        ],
        'swarming_dimensions': {
          'os': 'Mac-10.9',
          'cpu': 'x86-64',
        },
        'testing': {'platform': 'mac'},
      },
      'v8_mac64_dbg': {
        'chromium_apply_config': [
          'v8_ninja', 'default_compiler', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [
          V8Testing(3),
          Test262,
          Mozilla,
        ],
        'swarming_dimensions': {
          'os': 'Mac-10.9',
          'cpu': 'x86-64',
        },
        'testing': {'platform': 'mac'},
      },
      'v8_mac_gc_stress_dbg': {
        'chromium_apply_config': [
          'v8_ninja', 'default_compiler', 'goma', 'mb'],
        'v8_apply_config': ['gc_stress'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [Mjsunit(3), Webkit],
        'swarming_dimensions': {
          'os': 'Mac-10.9',
          'cpu': 'x86-64',
        },
        'testing': {'platform': 'mac'},
      },
      'v8_mac64_asan_rel': {
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'goma',
          'no_dcheck',
          'mb',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [V8Testing(4)],
        'swarming_dimensions': {
          'os': 'Mac-10.9',
          'cpu': 'x86-64',
        },
        'testing': {'platform': 'mac'},
      },
      'v8_linux_arm_rel_ng': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_arm', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'enable_swarming': True,
        'slim_swarming_builder': True,
        'triggers': [
          'v8_linux_arm_rel_ng_triggered',
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_arm_rel_ng_triggered': {
        'chromium_apply_config': ['simulate_arm'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'v8_linux_arm_rel_ng',
        'enable_swarming': True,
        'tests': [
          V8Testing(7),
          Test262,
          Mozilla,
          MjsunitSPFrameAccess,
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_arm_dbg': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_arm', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [
          V8Testing(5),
          Test262,
          Mozilla,
          MjsunitSPFrameAccess,
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_arm_armv8a_rel': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_arm', 'mb'],
        'v8_apply_config': ['enable_armv8'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [V8Testing(3), Test262, Mozilla],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_arm_armv8a_dbg': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_arm', 'mb'],
        'v8_apply_config': ['enable_armv8'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [V8Testing(3), Test262, Mozilla],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_arm64_rel_ng': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_arm', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'enable_swarming': True,
        'slim_swarming_builder': True,
        'triggers': [
          'v8_linux_arm64_rel_ng_triggered',
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_arm64_rel_ng_triggered': {
        'chromium_apply_config': ['simulate_arm'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'tester',
        'parent_buildername': 'v8_linux_arm64_rel_ng',
        'enable_swarming': True,
        'tests': [
          V8Testing(7),
          Test262,
          Mozilla,
          MjsunitSPFrameAccess,
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_arm64_dbg': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_arm', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [
          V8Testing(4),
          Test262,
          Mozilla,
          MjsunitSPFrameAccess,
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux_arm64_gc_stress_dbg': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_arm', 'mb'],
        'v8_apply_config': ['gc_stress'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [Mjsunit(5), Webkit],
        'testing': {'platform': 'linux'},
      },
      'v8_android_arm_compile_rel': {
        'gclient_apply_config': ['android'],
        'chromium_apply_config': [
          'v8_ninja',
          'default_compiler',
          'goma',
          'no_dcheck',
          'mb',
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
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_mipsel',
          'no_dcheck', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'v8_linux_mips64el_compile_rel': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_mipsel',
          'no_dcheck', 'mb'],
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
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
      },
    },
  },
}

####### Waterfall: client.v8.branches
BRANCH_BUILDERS = {}

def AddBranchBuilder(name, build_config, bits, presubmit=False,
                     unittests_only=False):
  tests = []
  if presubmit:
    tests.append(Presubmit)
  if unittests_only:
    tests.append(Unittests)
  else:
    if build_config == 'Debug':
      tests.append(V8Testing(3))
    elif 'arm' in name:
      tests.append(V8Testing(2))
    else:
      tests.append(V8Testing)
    tests.extend([Test262, Mozilla])
  return {
    'chromium_apply_config': ['default_compiler', 'v8_ninja', 'goma', 'mb'],
    'v8_config_kwargs': {
      'BUILD_CONFIG': build_config,
      'TARGET_BITS': bits,
    },
    'enable_swarming': True,
    'bot_type': 'builder_tester',
    'tests': tests,
    'testing': {'platform': 'linux'},
    'swarming_properties': {
      'default_expiration': 2 * 60 * 60,
      'default_hard_timeout': 90 * 60,
      'default_priority': 35,
    },
  }

for build_config, name_suffix in (('Release', ''), ('Debug', ' - debug')):
  for branch_name in ('stable branch', 'beta branch'):
    name = 'V8 Linux - %s%s' % (branch_name, name_suffix)
    BRANCH_BUILDERS[name] = AddBranchBuilder(
        name, build_config, 32, presubmit=True)
    name = 'V8 Linux64 - %s%s' % (branch_name, name_suffix)
    BRANCH_BUILDERS[name] = AddBranchBuilder(name, build_config, 64)
    name = 'V8 arm - sim - %s%s' % (branch_name, name_suffix)
    BRANCH_BUILDERS[name] = AddBranchBuilder(name, build_config, 32)
    BRANCH_BUILDERS[name]['chromium_apply_config'].append('simulate_arm')

for branch_name in ('stable branch', 'beta branch'):
  name = 'V8 mipsel - sim - %s' % branch_name
  BRANCH_BUILDERS[name] = AddBranchBuilder(
      name, 'Release', 32, unittests_only=True)
  BRANCH_BUILDERS[name]['chromium_apply_config'].append('simulate_mipsel')

  name = 'V8 mips64el - sim - %s' % branch_name
  BRANCH_BUILDERS[name] = AddBranchBuilder(
      name, 'Release', 64, unittests_only=True)
  BRANCH_BUILDERS[name]['chromium_apply_config'].append('simulate_mipsel')

  name = 'V8 ppc - sim - %s' % branch_name
  BRANCH_BUILDERS[name] = AddBranchBuilder(
      name, 'Release', 32, unittests_only=True)
  BRANCH_BUILDERS[name]['chromium_apply_config'].append('simulate_ppc')

  name = 'V8 ppc64 - sim - %s' % branch_name
  BRANCH_BUILDERS[name] = AddBranchBuilder(
      name, 'Release', 64, unittests_only=True)
  BRANCH_BUILDERS[name]['chromium_apply_config'].append('simulate_ppc')

  name = 'V8 s390 - sim - %s' % branch_name
  BRANCH_BUILDERS[name] = AddBranchBuilder(
      name, 'Release', 32, unittests_only=True)
  BRANCH_BUILDERS[name]['chromium_apply_config'].append('simulate_s390')

  name = 'V8 s390x - sim - %s' % branch_name
  BRANCH_BUILDERS[name] = AddBranchBuilder(
      name, 'Release', 64, unittests_only=True)
  BRANCH_BUILDERS[name]['chromium_apply_config'].append('simulate_s390')

BUILDERS['client.v8.branches'] = {'builders': BRANCH_BUILDERS}

BUILDERS['client.dart.fyi'] = {'builders': {
  'v8-%s-release' % platform: {
    'chromium_apply_config': [
        'v8_ninja', 'default_compiler', 'goma', 'disassembler', 'mb'],
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

BUILDERS = freeze(BUILDERS)
BRANCH_BUILDERS = freeze(BRANCH_BUILDERS)

def iter_builders(recipe='v8'):
  """Iterates tuples of (mastername, builders, buildername, bot_config).

  Args:
    recipe: Limits iteration to a specific recipe (default: v8).
  """
  for mastername, master_config in BUILDERS.iteritems():
    builders = master_config['builders']
    for buildername, bot_config in builders.iteritems():
      if bot_config.get('recipe', 'v8') != recipe:
        continue
      yield mastername, builders, buildername, bot_config
