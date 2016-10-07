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


# Top-level test configs for convenience.
Benchmarks = TestStepConfig('benchmarks')
Deopt = TestStepConfig('deopt')
Fuzz = TestStepConfig('jsfunfuzz')
GCMole = TestStepConfig('gcmole')
IgnitionTurbofan = TestStepConfig('ignition_turbofan')
Mjsunit = TestStepConfig('mjsunit')
Mjsunit_2 = TestStepConfig('mjsunit', shards=2)
Mjsunit_3 = TestStepConfig('mjsunit', shards=3)
Mjsunit_4 = TestStepConfig('mjsunit', shards=4)
MjsunitExtra_3 = TestStepConfig('mjsunit_extra', shards=3)
MjsunitIgnitionTurbofan_2 = TestStepConfig(
    'mjsunit_ignition_turbofan', shards=2)
MjsunitSPFrameAccess = TestStepConfig('mjsunit_sp_frame_access')
Mozilla = TestStepConfig('mozilla')
OptimizeForSize = TestStepConfig('optimize_for_size')
Presubmit = TestStepConfig('presubmit')
SimdJs = TestStepConfig('simdjs')
SimpleLeak = TestStepConfig('simpleleak')
Test262 = TestStepConfig('test262')
Test262_2 = TestStepConfig('test262', shards=2)
Test262Extra_2 = TestStepConfig('test262_extra', shards=2)
Test262IgnitionTurbofan = TestStepConfig('test262_ignition_turbofan')
Test262IgnitionTurbofan_2 = TestStepConfig(
    'test262_ignition_turbofan', shards=2)
Test262Variants = TestStepConfig('test262_variants')
Test262Variants_2 = TestStepConfig('test262_variants', shards=2)
Test262Variants_3 = TestStepConfig('test262_variants', shards=3)
Test262Variants_6 = TestStepConfig('test262_variants', shards=6)
Unittests = TestStepConfig('unittests')
V8Initializers = TestStepConfig('v8initializers')
V8Testing = TestStepConfig('v8testing')
V8Testing_2 = TestStepConfig('v8testing', shards=2)
V8Testing_3 = TestStepConfig('v8testing', shards=3)
V8Testing_4 = TestStepConfig('v8testing', shards=4)
V8Testing_5 = TestStepConfig('v8testing', shards=5)
V8TestingExtra = TestStepConfig('v8testing_extra')
V8TestingExtra_2 = TestStepConfig('v8testing_extra', shards=2)
Webkit = TestStepConfig('webkit')


def with_test_args(suffix, test_args, tests, variants=V8VariantNeutral):
  """Wrapper that runs a list of tests with additional arguments."""
  return [
    TestStepConfig(t.name, t.shards, t.swarming, suffix, test_args, variants)
    for t in tests
  ]


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
        'triggers': [
          'V8 Deopt Fuzzer',
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
          V8TestingExtra,
          OptimizeForSize,
          Benchmarks,
          SimdJs,
          Test262Variants_2,
          Test262Extra_2,
          Mozilla,
          IgnitionTurbofan,
          MjsunitSPFrameAccess,
          Test262IgnitionTurbofan,
          GCMole,
        ] + with_test_args(
            'isolates',
            ['--isolates'],
            [V8Testing],
        ) + with_test_args(
            'nosse3',
            ['--extra-flags', '--noenable-sse3 --noenable-avx'],
            [V8Testing, Mozilla, SimdJs],
        ) + with_test_args(
            'nosse4',
            ['--extra-flags', '--noenable-sse4-1 --noenable-avx'],
            [V8Testing, Mozilla, SimdJs],
        ) + with_test_args(
            'deadcode',
            ['--extra-flags=--dead-code-elimination'],
            [V8Testing, Test262, Mozilla, SimdJs],
        ),
        'testing': {'platform': 'linux'},
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-12.04',
        },
      },
      'V8 Linux - swarming staging': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [
          V8Initializers,
          V8Testing,
          OptimizeForSize,
          Test262Variants_2,
          Mozilla,
          SimdJs,
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
        'enable_swarming': True,
        'tests': [
          V8Testing,
          V8TestingExtra_2,
          Benchmarks,
          Test262Variants_3,
          Test262Extra_2,
          Mozilla,
          SimdJs,
          IgnitionTurbofan,
          MjsunitSPFrameAccess,
          Test262IgnitionTurbofan,
        ] + with_test_args(
            'isolates',
            ['--isolates'],
            [V8Testing_2],
        ) + with_test_args(
            'nosse3',
            ['--extra-flags', '--noenable-sse3 --noenable-avx'],
            [V8Testing, Test262, Mozilla, SimdJs],
        ) + with_test_args(
            'nosse4',
            ['--extra-flags', '--noenable-sse4-1 --noenable-avx'],
            [V8Testing, Test262, Mozilla, SimdJs],
        ) + with_test_args(
            'code serializer',
            ['--extra-flags', '--serialize-toplevel --cache=code'],
            [Mjsunit, Mozilla, Test262, Benchmarks, SimdJs],
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
        'tests': [V8Testing, Benchmarks, Mozilla, SimdJs],
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'pool': 'V8-AVX2',
          'gpu': '102b',
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
        'tests': [V8Testing, Test262, Mozilla, SimdJs],
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
        'enable_swarming': True,
        'tests': [
          V8Testing_2,
          SimdJs,
          Test262,
          Mozilla,
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - nosnap - debug': {
        'v8_apply_config': ['no_snapshot'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'V8 Linux - nosnap debug builder',
        'build_gs_archive': 'linux_nosnap_dbg_archive',
        'enable_swarming': True,
        'tests': [V8Testing_4, Mozilla, SimdJs],
        'testing': {'platform': 'linux'},
        'swarming_properties': {
          'default_hard_timeout': 60 * 60,
        },
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
      },
      'V8 Linux - noi18n - debug': {
        'v8_apply_config': ['no_i18n'],
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'no_i18n', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'tests': [V8Testing, Mozilla, Test262, SimdJs],
        'variants': V8NoExhaustiveVariants(),
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
        'triggers': [
          'V8 Linux64',
          'V8 Linux64 - avx2',
        ],
        'triggers_proxy': True,
      },
      'V8 Linux64 - debug builder': {
        'gclient_apply_config': ['v8_valgrind'],
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'jsfunfuzz', 'has_valgrind',
          'mb'],
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
          V8TestingExtra,
          OptimizeForSize,
          Test262Variants_2,
          Test262Extra_2,
          Mozilla,
          SimdJs,
          IgnitionTurbofan,
          MjsunitSPFrameAccess,
          Test262IgnitionTurbofan,
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
          SimdJs,
        ],
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'pool': 'V8-AVX2',
          'gpu': '102b',
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
          V8Testing,
          V8TestingExtra,
          Test262Variants_3,
          Test262Extra_2,
          Mozilla,
          SimdJs,
          IgnitionTurbofan,
          MjsunitSPFrameAccess,
          Test262IgnitionTurbofan,
          SimpleLeak,
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
          V8Testing,
          Benchmarks,
          Mozilla,
          SimdJs,
        ],
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'pool': 'V8-AVX2',
          'gpu': '102b',
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
####### Category: Windows
      'V8 Win32 - builder': {
        'chromium_apply_config': [
          'default_compiler',
          'v8_ninja',
          'goma',
          'mb',
          'msvs2013',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'win32_rel_archive',
        'enable_swarming': True,
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
          'msvs2013',
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
        'tests': [
          V8Testing, V8TestingExtra, Test262, Mozilla, IgnitionTurbofan],
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86-64',
        },
      },
      'V8 Win32 - nosnap - shared': {
        'v8_apply_config': ['no_snapshot'],
        'chromium_apply_config': [
          'default_compiler',
          'v8_ninja',
          'goma',
          'shared_library',
          'no_snapshot',
          'mb',
          'msvs2013',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [V8Testing_2, V8TestingExtra_2, IgnitionTurbofan],
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
          V8Testing_2,
          V8TestingExtra_2,
          Test262,
          Mozilla,
          IgnitionTurbofan,
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
          'msvs2013',
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
        'tests': [
          V8Testing,
          V8TestingExtra,
          SimdJs,
          Test262,
          Mozilla,
          IgnitionTurbofan,
        ],
        'testing': {'platform': 'win'},
      },
      'V8 Win64 - debug': {
        'chromium_apply_config': [
          'default_compiler',
          'v8_ninja',
          'goma',
          'mb',
          'msvs2013',
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
          V8Testing_2,
          V8TestingExtra_2,
          SimdJs,
          Test262,
          Mozilla,
          IgnitionTurbofan,
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
        'tests': [
          V8Testing,
          V8TestingExtra,
          Test262,
          Mozilla,
          SimdJs,
          IgnitionTurbofan,
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
          V8Testing,
          V8TestingExtra_2,
          Test262,
          Mozilla,
          SimdJs,
          IgnitionTurbofan,
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
        'tests': [
          V8Testing,
          V8TestingExtra,
          Test262,
          Mozilla,
          SimdJs,
          IgnitionTurbofan,
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
          V8Testing,
          V8TestingExtra_2,
          Test262,
          Mozilla,
          SimdJs,
          IgnitionTurbofan,
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
      },
      'V8 Deopt Fuzzer': {
        'v8_apply_config': ['deopt_fuzz_normal'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'enable_swarming': True,
        'parent_buildername': 'V8 Linux - builder',
        'build_gs_archive': 'linux_rel_archive',
        'tests': [Deopt],
        'variants': V8NoExhaustiveVariants(),
        'testing': {'platform': 'linux'},
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
        'tests': [
          Mjsunit_4,
          MjsunitExtra_3,
          Webkit,
          MjsunitIgnitionTurbofan_2,
        ],
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
        'tests': [Mjsunit_3, Webkit],
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
        'tests': [Mjsunit_3],
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
      'V8 Linux64 ASAN': {
        'chromium_apply_config': [
          'v8_ninja', 'clang', 'asan', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
        },
        'tests': [
          V8Testing_2,
          V8TestingExtra_2,
          Test262,
          IgnitionTurbofan,
        ],
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
          'mb',
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
          'mb',
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
          'mb',
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
          'mb',
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
          'mb',
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
        'chromium_apply_config': [
          'v8_ninja', 'clang', 'tsan2', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
        },
        'tests': [
          V8Testing_3,
          V8TestingExtra_2,
          Test262_2,
          IgnitionTurbofan,
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm64 - sim - MSAN': {
        # 'simulate_arm' is actually implied by 'msan'. We still set it
        # explicitly for the sake of consistency.
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'msan',
          'msan_full_origin_tracking',
          'prebuilt_instrumented_libraries',
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
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
        },
        'tests': [
          V8Testing_4,
          V8TestingExtra_2,
          Test262,
          IgnitionTurbofan,
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux64 - cfi': {
        'chromium_apply_config': [
          'v8_ninja', 'default_compiler', 'goma', 'cfi', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
        },
        'tests': [
          V8Testing,
          V8TestingExtra_2,
          OptimizeForSize,
          Benchmarks,
          Test262,
          Mozilla,
          SimdJs,
          IgnitionTurbofan,
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Mac64 ASAN': {
        'chromium_apply_config': [
          'v8_ninja', 'clang', 'asan', 'goma', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [V8Testing_4, V8TestingExtra_2, IgnitionTurbofan],
        'swarming_dimensions': {
          'os': 'Mac-10.9',
          'cpu': 'x86-64',
        },
        'testing': {'platform': 'mac'},
      },
####### Category: FYI
      'V8 Linux64 - gcov coverage': {
      'v8_apply_config': ['gcov_coverage'],
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
        'v8_apply_config': ['predictable'],
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
        'testing': {'platform': 'linux'},
      },
      'V8 Random Deopt Fuzzer - debug': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'mb'],
        'v8_apply_config': ['deopt_fuzz_random'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'swarming_properties': {
          'default_hard_timeout': 4 * 60 * 60,
        },
        'tests': [Deopt],
        'variants': V8NoExhaustiveVariants(),
        'testing': {'platform': 'linux'},
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
          V8Testing,
          Benchmarks,
          OptimizeForSize,
          SimdJs,
          IgnitionTurbofan,
          Test262IgnitionTurbofan,
        ],
        'enable_swarming': True,
        'swarming_properties': {
          'default_hard_timeout': 90 * 60,
          'default_expiration': 6 * 60 * 60,
        },
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'cpu': 'armv7l',
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Arm - debug': {
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'build_gs_archive': 'arm_dbg_archive',
        'parent_buildername': 'V8 Arm - debug builder',
        'tests': [
          V8Testing_2,
          OptimizeForSize,
          SimdJs,
        ],
        'variants': V8NoExhaustiveVariants(),
        'enable_swarming': True,
        'swarming_properties': {
          'default_hard_timeout': 60 * 60,
          'default_expiration': 6 * 60 * 60,
        },
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'cpu': 'armv7l',
        },
        'testing': {'platform': 'linux'},
      },
      'V8 Arm GC Stress': {
        'v8_apply_config': ['gc_stress'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'build_gs_archive': 'arm_dbg_archive',
        'parent_buildername': 'V8 Arm - debug builder',
        'tests': [Mjsunit_2, Webkit],
        'variants': V8Variant('default'),
        'enable_swarming': True,
        'swarming_properties': {
          'default_hard_timeout': 2 * 60 * 60,
          'default_expiration': 6 * 60 * 60,
        },
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'cpu': 'armv7l',
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
          V8Testing_2,
          V8TestingExtra_2,
          Test262,
          Test262Extra_2,
          Mozilla,
          SimdJs,
          IgnitionTurbofan,
          MjsunitSPFrameAccess,
          Test262IgnitionTurbofan,
        ] + with_test_args(
            'armv8-a',
            ['--extra-flags', '--enable-armv8'],
            [V8Testing_2, Test262, Mozilla, SimdJs],
        ) + with_test_args(
            'novfp3',
            ['--novfp3'],
            [V8Testing_2, Test262, Mozilla, SimdJs],
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
          V8Testing_2,
          V8TestingExtra_2,
          Test262,
          Test262Extra_2,
          Mozilla,
          SimdJs,
          IgnitionTurbofan,
          MjsunitSPFrameAccess,
          Test262IgnitionTurbofan,
        ] + with_test_args(
            'armv8-a',
            ['--extra-flags', '--enable-armv8'],
            [V8Testing_2, Test262, Mozilla, SimdJs],
        ) + with_test_args(
            'novfp3',
            ['--novfp3'],
            [V8Testing_2, Test262, Mozilla, SimdJs],
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
          V8Testing_2,
          V8TestingExtra_2,
          Test262,
          Test262Extra_2,
          Mozilla,
          SimdJs,
          IgnitionTurbofan,
          MjsunitSPFrameAccess,
          Test262IgnitionTurbofan,
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
          V8Testing_2,
          V8TestingExtra_2,
          Test262,
          Test262Extra_2,
          Mozilla,
          SimdJs,
          IgnitionTurbofan,
          MjsunitSPFrameAccess,
          Test262IgnitionTurbofan,
        ],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - arm64 - sim - nosnap - debug': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_arm',
          'no_snapshot', 'mb'],
        'v8_apply_config': ['no_snapshot'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'tests': [V8Testing_5, Test262_2, Mozilla, SimdJs],
        'testing': {'platform': 'linux'},
        'swarming_properties': {
          'default_expiration': 2 * 60 * 60,
          'default_hard_timeout': 60 * 60,
          'default_priority': 35,
        },
      },
      'V8 Linux - arm64 - sim - gc stress': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_arm', 'mb'],
        'v8_apply_config': ['gc_stress'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'swarming_properties': {
          'default_expiration': 2 * 60 * 60,
          'default_hard_timeout': 90 * 60,
          'default_priority': 35,
        },
        'tests': [Mjsunit_3, Webkit],
        'testing': {'platform': 'linux'},
      },
####### Category: MIPS
      'V8 Mips - builder': {
        # TODO(machenbach): Switch this bot manually to gn.
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
        'tests': [V8Testing, SimdJs],
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
        'tests': [V8Testing, SimdJs],
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
        'tests': [V8Testing, Test262, SimdJs],
        'testing': {'platform': 'linux'},
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
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - ppc64 - sim': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_ppc', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
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
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
      },
      'V8 Linux - s390x - sim': {
        'chromium_apply_config': [
          'default_compiler', 'v8_ninja', 'goma', 'simulate_s390', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'tests': [V8Testing],
        'testing': {'platform': 'linux'},
      },
####### Category: X87
      'V8 Linux - x87 - nosnap - debug builder': {
        'v8_apply_config': ['no_snapshot'],
        'chromium_apply_config': [
          'v8_ninja', 'default_compiler', 'goma', 'no_snapshot',  'x87', 'mb'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'enable_swarming': True,
        'build_gs_archive': 'linux_x87_nosnap_dbg_archive',
        'testing': {'platform': 'linux'},
        'triggers': [
          'V8 Linux - x87 - nosnap - debug',
        ],
      },
      'V8 Linux - x87 - nosnap - debug': {
        'v8_apply_config': ['no_snapshot'],
        'chromium_apply_config': [
          'v8_ninja', 'default_compiler', 'goma', 'no_snapshot', 'x87'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'enable_swarming': True,
        'parent_buildername': 'V8 Linux - x87 - nosnap - debug builder',
        'build_gs_archive': 'linux_x87_nosnap_dbg_archive',
        'tests': [V8Testing_2],
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
        },
        'swarming_properties': {
          'default_expiration': 2 * 60 * 60,
          'default_hard_timeout': 2 * 60 * 60,
          'default_priority': 35,
        },
      },
    },
  },
####### Waterfall: tryserver.v8
  'tryserver.v8': {
    'builders': {
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
          V8TestingExtra,
          OptimizeForSize,
          Test262Variants_2,
          Test262Extra_2,
          Mozilla,
          Benchmarks,
          SimdJs,
          IgnitionTurbofan,
          MjsunitSPFrameAccess,
          Test262IgnitionTurbofan,
          GCMole,
        ],
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
          V8Testing_2,
          SimdJs,
        ],
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'pool': 'V8-AVX2',
          'gpu': '102b',
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
          V8TestingExtra,
          Test262Variants_2,
          Test262Extra_2,
          Test262IgnitionTurbofan,
          IgnitionTurbofan,
          Mozilla,
          Benchmarks,
          SimdJs,
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
          V8Testing_2,
          V8TestingExtra_2,
          Test262,
          Mozilla,
          Benchmarks,
          SimdJs,
          IgnitionTurbofan,
          MjsunitSPFrameAccess,
          Test262IgnitionTurbofan,
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
        'v8_apply_config': ['no_i18n'],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'v8_linux_noi18n_rel_ng',
        'enable_swarming': True,
        'tests': [
          V8Testing_2,
          Test262,
          Mozilla,
          SimdJs,
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
        'tests': [V8Testing_3],
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
        'tests': [V8Testing_4],
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
          V8TestingExtra,
          OptimizeForSize,
          Test262Variants_2,
          Test262Extra_2,
          SimdJs,
          IgnitionTurbofan,
          MjsunitSPFrameAccess,
          Test262IgnitionTurbofan,
        ],
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
          SimdJs,
        ],
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'pool': 'V8-AVX2',
          'gpu': '102b',
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
          V8Testing_2,
          SimdJs,
        ],
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'pool': 'V8-AVX2',
          'gpu': '102b',
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
          Mjsunit_4,
          MjsunitExtra_3,
          Webkit,
          MjsunitIgnitionTurbofan_2,
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_asan_rel_ng': {
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'asan',
          'goma',
          'mb',
          'no_dcheck',
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
        'bot_type': 'tester',
        'parent_buildername': 'v8_linux64_asan_rel_ng',
        'enable_swarming': True,
        'tests': [
          V8Testing_2,
          V8TestingExtra_2,
          Test262_2,
          IgnitionTurbofan,
        ],
        # TODO(machenbach): Run with exhaustive variants as soon as bot runs
        # on swarming.
        'variants': V8NoExhaustiveVariants(),
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
        },
      },
      'v8_linux64_msan_rel': {
        # 'simulate_arm' is actually implied by 'msan'. We still set it
        # explicitly for the sake of consistency.
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'msan',
          'msan_full_origin_tracking',
          'prebuilt_instrumented_libraries',
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
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
        },
        'tests': [
          V8Testing_5,
          V8TestingExtra_2,
          Test262_2,
          IgnitionTurbofan,
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_tsan_rel': {
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'tsan2',
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
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
        },
        'tests': [
          V8Testing_4,
          V8TestingExtra_2,
          Test262_2,
          IgnitionTurbofan,
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_linux64_sanitizer_coverage_rel': {
        'gclient_apply_config': ['llvm_compiler_rt'],
        'chromium_apply_config': [
          'v8_ninja',
          'clang',
          'coverage',
          'asan',
          'goma',
          'mb',
          'no_dcheck',
          'sanitizer_bb_coverage',
        ],
        'v8_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
        },
        'sanitizer_coverage_folder': 'linux64',
        'tests': [
          V8Testing_3,
          OptimizeForSize,
          Test262Variants_6,
          SimdJs,
          IgnitionTurbofan,
          MjsunitSPFrameAccess,
          Test262IgnitionTurbofan_2,
        ],
        'testing': {'platform': 'linux'},
      },
      'v8_win_dbg': {
        'chromium_apply_config': [
          'default_compiler',
          'v8_ninja',
          'goma',
          'mb',
          'msvs2013',
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
          V8Testing_2,
          V8TestingExtra_2,
          IgnitionTurbofan,
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
          'msvs2013',
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
          'msvs2013',
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
        'tests': [V8Testing, V8TestingExtra, IgnitionTurbofan],
        'testing': {'platform': 'linux'},
      },
      'v8_win_nosnap_shared_rel_ng': {
        'v8_apply_config': ['no_snapshot'],
        'chromium_apply_config': [
          'default_compiler',
          'v8_ninja',
          'goma',
          'no_dcheck',
          'no_snapshot',
          'shared_library',
          'mb',
          'msvs2013',
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
        'v8_apply_config': ['no_snapshot'],
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
        'tests': [V8Testing_2, V8TestingExtra_2, IgnitionTurbofan],
        'testing': {'platform': 'linux'},
      },
      'v8_win64_rel_ng': {
        'chromium_apply_config': [
          'default_compiler',
          'v8_ninja',
          'goma',
          'mb',
          'msvs2013',
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
        'tests': [V8Testing, V8TestingExtra, SimdJs, IgnitionTurbofan],
        'testing': {'platform': 'linux'},
      },
      'v8_win64_dbg': {
        'chromium_apply_config': [
          'default_compiler',
          'v8_ninja',
          'goma',
          'mb',
          'msvs2013',
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
          V8Testing_2,
          V8TestingExtra_2,
          SimdJs,
          IgnitionTurbofan,
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
          V8TestingExtra,
          Test262,
          Mozilla,
          SimdJs,
          IgnitionTurbofan,
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
          V8Testing_2,
          V8TestingExtra_2,
          Test262,
          Mozilla,
          SimdJs,
          IgnitionTurbofan,
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
          V8TestingExtra,
          Test262,
          Mozilla,
          SimdJs,
          IgnitionTurbofan,
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
          V8Testing_2,
          V8TestingExtra_2,
          Test262,
          Mozilla,
          SimdJs,
          IgnitionTurbofan,
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
        'tests': [Mjsunit_3, Webkit],
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
          'asan',
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
        'tests': [V8Testing_4],
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
          V8Testing_3,
          V8TestingExtra_2,
          Test262,
          Test262Extra_2,
          Mozilla,
          SimdJs,
          IgnitionTurbofan,
          MjsunitSPFrameAccess,
          Test262IgnitionTurbofan_2,
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
          V8Testing_3,
          V8TestingExtra_2,
          Test262,
          Test262Extra_2,
          Mozilla,
          SimdJs,
          IgnitionTurbofan,
          MjsunitSPFrameAccess,
          Test262IgnitionTurbofan_2,
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
        'tests': [V8Testing_3, Test262, Mozilla, SimdJs],
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
        'tests': [V8Testing_3, Test262, Mozilla, SimdJs],
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
          V8Testing_3,
          V8TestingExtra_2,
          Test262,
          Test262Extra_2,
          Mozilla,
          SimdJs,
          IgnitionTurbofan,
          MjsunitSPFrameAccess,
          Test262IgnitionTurbofan_2,
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
          V8Testing_3,
          V8TestingExtra_2,
          Test262,
          Test262Extra_2,
          Mozilla,
          SimdJs,
          IgnitionTurbofan,
          MjsunitSPFrameAccess,
          Test262IgnitionTurbofan_2,
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
        'tests': [Mjsunit_3, Webkit],
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

def AddBranchBuilder(build_config, arch, bits, presubmit=False,
                     unittests_only=False):
  if unittests_only:
    tests = [Unittests]
  else:
    tests = [V8Testing, Test262, Mozilla]
  if presubmit:
    tests = [Presubmit] + tests
  return {
    'chromium_apply_config': ['default_compiler', 'v8_ninja', 'goma', 'mb'],
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
  for branch_name in ('stable branch', 'beta branch'):
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

  name = 'V8 s390 - sim - %s' % branch_name
  BRANCH_BUILDERS[name] = AddBranchBuilder(
      'Release', 'intel', 32, unittests_only=True)
  BRANCH_BUILDERS[name]['chromium_apply_config'].append('simulate_s390')

  name = 'V8 s390x - sim - %s' % branch_name
  BRANCH_BUILDERS[name] = AddBranchBuilder(
      'Release', 'intel', 64, unittests_only=True)
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

win = BUILDERS['client.dart.fyi']['builders']['v8-win-release']
win['chromium_apply_config'].extend(['msvs2013'])

BUILDERS = freeze(BUILDERS)
BRANCH_BUILDERS = freeze(BRANCH_BUILDERS)

def iter_builders():
  for mastername, master_config in BUILDERS.iteritems():
    builders = master_config['builders']
    for buildername, bot_config in builders.iteritems():
      yield mastername, builders, buildername, bot_config
