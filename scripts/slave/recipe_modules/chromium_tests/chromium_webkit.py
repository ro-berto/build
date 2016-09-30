# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-webkit-archive',
    'src_side_runtest_py': False,
  },
}

SPEC['builders'] = {
  'WebKit Win Builder': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['mb'],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 32,
    },
    'bot_type': 'builder',
    'testing': {
      'platform': 'win',
    },
    'enable_swarming': True,
    'use_isolate': True,
    'checkout_dir': 'win_layout',
  },
  'WebKit Win7': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['mb'],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 32,
    },
    'bot_type': 'tester',
    'parent_buildername': 'WebKit Win Builder',
    'tests': [
      steps.BlinkTest(),
    ],
    'testing': {
      'platform': 'win',
    },
    'enable_swarming': True,
    'use_isolate': True,
    'checkout_dir': 'win_layout',
  },
  'WebKit Win10': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['mb'],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 32,
    },
    'bot_type': 'tester',
    'parent_buildername': 'WebKit Win Builder',
    'tests': [
      steps.BlinkTest(),
    ],
    'testing': {
      'platform': 'win',
    },
    'enable_swarming': True,
    'use_isolate': True,
    'checkout_dir': 'win_layout',
  },
  'WebKit Win x64 Builder': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['mb'],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 64,
    },
    'compile_targets': [
      # TODO(phajdan.jr): Shouldn't be needed once we have 64-bit testers.
      'blink_tests',
    ],
    'bot_type': 'builder_tester',
    'testing': {
      'platform': 'win',
    },
    'enable_swarming': True,
    'use_isolate': True,
    'checkout_dir': 'win_layout',
  },
  'WebKit Win Builder (dbg)': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['mb'],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Debug',
      'TARGET_BITS': 32,
    },
    'bot_type': 'builder',
    'testing': {
      'platform': 'win',
    },
    'enable_swarming': True,
    'use_isolate': True,
    'checkout_dir': 'win_layout',
  },
  'WebKit Win7 (dbg)': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['mb'],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Debug',
      'TARGET_BITS': 32,
    },
    'bot_type': 'tester',
    'parent_buildername': 'WebKit Win Builder (dbg)',
    'tests': [
      steps.BlinkTest(),
    ],
    'testing': {
      'platform': 'win',
    },
    'enable_swarming': True,
    'use_isolate': True,
    'checkout_dir': 'win_layout',
  },
  'WebKit Win x64 Builder (dbg)': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['mb'],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Debug',
      'TARGET_BITS': 64,
    },
    'compile_targets': [
      # TODO(phajdan.jr): Shouldn't be needed once we have 64-bit testers.
      'blink_tests',
    ],
    'bot_type': 'builder_tester',
    'testing': {
      'platform': 'win',
    },
    'enable_swarming': True,
    'use_isolate': True,
    'checkout_dir': 'win_layout',
  },
  'WebKit Mac Builder': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['mb'],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 64,
    },
    'bot_type': 'builder',
    'testing': {
      'platform': 'mac',
    },
    'enable_swarming': True,
    'swarming_dimensions': {
      'os': 'Mac-10.11',
    },
    'use_isolate': True,
    'checkout_dir': 'mac_layout',
  },
  'WebKit Mac10.11 (retina)': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['mb'],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 64,
    },
    'compile_targets': [
      'blink_tests',
    ],
    'tests': [
      steps.BlinkTest(),
    ],
    'testing': {
      'platform': 'mac',
    },
    'enable_swarming': True,
    'swarming_dimensions': {
      'os': 'Mac-10.11',
      'hidpi': '1',
    },
    'use_isolate': True,
    'checkout_dir': 'mac_layout',
  },
  'WebKit Mac10.9': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['mb'],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 64,
    },
    'bot_type': 'builder',
    'tests': [
      steps.BlinkTest(),
    ],
    'testing': {
      'platform': 'mac',
    },
    'enable_swarming': True,
    'swarming_dimensions': {
      'os': 'Mac-10.9',
    },
    'use_isolate': True,
    'checkout_dir': 'mac_layout',
  },
  'WebKit Mac10.10': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['mb'],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 64,
    },
    'bot_type': 'tester',
    'parent_buildername': 'WebKit Mac Builder',
    'tests': [
      steps.BlinkTest(),
    ],
    'testing': {
      'platform': 'mac',
    },
    'enable_swarming': True,
    'swarming_dimensions': {
      'os': 'Mac-10.10',
    },
    'use_isolate': True,
    'checkout_dir': 'mac_layout',
  },
  'WebKit Mac10.11': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['mb'],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 64,
    },
    'bot_type': 'tester',
    'parent_buildername': 'WebKit Mac Builder',
    'tests': [
      steps.BlinkTest(),
    ],
    'testing': {
      'platform': 'mac',
    },
    'enable_swarming': True,
    'swarming_dimensions': {
      'os': 'Mac-10.11',
    },
    'use_isolate': True,
    'checkout_dir': 'mac_layout',
  },
  'WebKit Mac Builder (dbg)': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['mb'],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Debug',
      'TARGET_BITS': 64,
    },
    'bot_type': 'builder',
    'testing': {
      'platform': 'mac',
    },
    'enable_swarming': True,
    'swarming_dimensions': {
      'os': 'Mac-10.11',
    },
    'use_isolate': True,
    'checkout_dir': 'mac_layout',
  },
  'WebKit Mac10.11 (dbg)': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['mb'],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Debug',
      'TARGET_BITS': 64,
    },
    'bot_type': 'tester',
    'parent_buildername': 'WebKit Mac Builder (dbg)',
    'tests': [
      steps.BlinkTest(),
    ],
    'testing': {
      'platform': 'mac',
    },
    'enable_swarming': True,
    'swarming_dimensions': {
      'os': 'Mac-10.11',
    },
    'use_isolate': True,
    'checkout_dir': 'mac_layout',
  },
  'WebKit Linux Precise': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 64,
    },
    'compile_targets': [
      'blink_tests',
    ],
    'tests': [
      steps.BlinkTest(),
    ],
    'testing': {
      'platform': 'linux',
    },
    'enable_swarming': True,
    'use_isolate': True,
    'checkout_dir': 'linux_layout',
  },
  'WebKit Linux Trusty': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['mb'],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 64,
    },
    'compile_targets': [
      'blink_tests',
    ],
    'tests': [
      steps.BlinkTest(),
    ],
    'testing': {
      'platform': 'linux',
    },
    'enable_swarming': True,
    'use_isolate': True,
    'checkout_dir': 'linux_layout',
  },
  'WebKit Linux Precise ASAN': {
    'chromium_config': 'chromium_clang',
    'chromium_apply_config': ['asan', 'mb'],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 64,
    },
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
    'checkout_dir': 'linux_layout',
  },
  'WebKit Linux Precise MSAN': {
    'chromium_config': 'chromium_clang',
    'gclient_config': 'chromium',
    'chromium_apply_config': [
      'mb',
      'msan',
      'msan_full_origin_tracking',
      'prebuilt_instrumented_libraries',
    ],
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 64,
    },
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
    'checkout_dir': 'linux_layout',
  },
  'WebKit Linux Precise (dbg)': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['mb'],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Debug',
      'TARGET_BITS': 64,
    },
    'tests': [
      steps.BlinkTest(),
    ],
    'testing': {
      'platform': 'linux',
    },
    'enable_swarming': True,
    'use_isolate': True,
    'checkout_dir': 'linux_layout',
  },
  'Android Builder': {
    'chromium_config': 'android',
    'chromium_apply_config': ['mb'],
    'gclient_config': 'chromium',
    'gclient_apply_config': ['android'],
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 32,
      'TARGET_PLATFORM': 'android',
    },
    'android_config': 'main_builder',
    'bot_type': 'builder',
    'testing': {
      'platform': 'linux',
    },
  },
  'WebKit Android (Nexus4)': {
    'chromium_config': 'android',
    'chromium_apply_config': ['mb'],
    'gclient_config': 'chromium',
    'gclient_apply_config': ['android'],
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 32,
      'TARGET_PLATFORM': 'android',
    },
    'bot_type': 'tester',
    'parent_buildername': 'Android Builder',
    'android_config': 'main_builder',
    'root_devices': True,
    'tests': [
      steps.GTestTest('blink_heap_unittests'),
      steps.GTestTest('webkit_unit_tests'),
      steps.BlinkTest(),
    ],
    'testing': {
      'platform': 'linux',
    },
  },
  'WebKit Linux Precise Leak': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['mb'],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 64,
    },
    'compile_targets': [
      'blink_tests',
    ],
    'tests': [
      steps.BlinkTest(extra_args=[
          '--additional-expectations',
          'src/third_party/WebKit/LayoutTests/LeakExpectations',
          '--options=--enable-leak-detection',
      ]),
    ],
    'testing': {
      'platform': 'linux',
    },
    'enable_swarming': True,
    'use_isolate': True,
  },
}
