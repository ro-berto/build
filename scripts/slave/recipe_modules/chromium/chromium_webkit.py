# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy

from . import chromium_chromiumos
from . import steps

SPEC = copy.deepcopy(chromium_chromiumos.SPEC)
for b in SPEC['builders'].itervalues():
    b['gclient_apply_config'] = ['blink']

SPEC['settings']['build_gs_bucket'] = 'chromium-webkit-archive'

SPEC['builders'].update({
  'WebKit Linux': {
    'recipe_config': 'chromium',
    'gclient_apply_config': ['blink_or_chromium'],
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 64,
    },
    'compile_targets': [
      'blink_tests',
    ],
    'test_generators': [
      steps.generate_gtest,
      steps.generate_script,
    ],
    'tests': [
      steps.BlinkTest(),
    ],
    'testing': {
      'platform': 'linux',
    },
    'enable_swarming': True,
    'use_isolate': True,
  },
  'WebKit Linux 32': {
    'recipe_config': 'chromium',
    'gclient_apply_config': ['blink_or_chromium'],
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 32,
    },
    'test_generators': [
      steps.generate_gtest,
      steps.generate_script,
    ],
    'tests': [
      steps.BlinkTest(),
    ],
    'testing': {
      'platform': 'linux',
    },
    'enable_swarming': True,
    'use_isolate': True,
  },
  'WebKit Linux ASAN': {
    'recipe_config': 'chromium_clang',
    'chromium_apply_config': ['asan'],
    'gclient_apply_config': ['blink_or_chromium'],
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 64,
    },
    'test_generators': [
      steps.generate_gtest,
      steps.generate_script,
    ],
    'tests': [
      steps.BlinkTest(extra_args=[
          '--additional-expectations',
          'src/third_party/WebKit/LayoutTests/ASANExpectations',
          # ASAN is roughly 8x slower than Release.
          '--time-out-ms', '48000',
          '--options=--enable-sanitizer',
      ]),
    ],
    'testing': {
      'platform': 'linux',
    },
    'enable_swarming': True,
    'use_isolate': True,
  },
  'WebKit Linux MSAN': {
    'recipe_config': 'chromium_clang',
    'chromium_apply_config': [
      'instrumented_libraries',
      'msan',
      'msan_full_origin_tracking',
    ],
    'gclient_apply_config': ['blink_or_chromium'],
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 64,
    },
    'test_generators': [
      steps.generate_gtest,
      steps.generate_script,
    ],
    'tests': [
      steps.BlinkTest(extra_args=[
          '--additional-expectations',
          'src/third_party/WebKit/LayoutTests/MSANExpectations',
          # Because JS code is run on a simulator, the slowdown in JS-heavy
          # tests will be much higher than MSan's average of 3x.
          '--time-out-ms', '66000',
          '--options=--enable-sanitizer',
      ]),
    ],
    'testing': {
      'platform': 'linux',
    },
    'enable_swarming': True,
    'use_isolate': True,
  },
  'WebKit Linux (dbg)': {
    'recipe_config': 'chromium',
    'gclient_apply_config': ['blink_or_chromium'],
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Debug',
      'TARGET_BITS': 64,
    },
    'test_generators': [
      steps.generate_gtest,
      steps.generate_script,
    ],
    'tests': [
      steps.BlinkTest(),
    ],
    'testing': {
      'platform': 'linux',
    },
    'enable_swarming': True,
    'use_isolate': True,
  },
})
