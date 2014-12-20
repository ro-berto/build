# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-v8',
  },
  'builders': {
    'Linux Debug Builder': {
      'recipe_config': 'chromium_v8',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      'testing': {
        'platform': 'linux',
        'test_spec_file': 'chromium.linux.json',
      },
    },
    # Bot names should be in sync with chromium.linux's names to retrieve the
    # same test configuration files.
    'Linux Tests (dbg)(1)': {
      'recipe_config': 'chromium_v8',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'parent_buildername': 'Linux Debug Builder',
      'testing': {
        'platform': 'linux',
        'test_spec_file': 'chromium.linux.json',
      },
    },
    'Linux ASAN Builder': {
      'recipe_config': 'chromium_linux_asan',
      'gclient_apply_config': [
        'v8_bleeding_edge_git',
        'chromium_lkcr',
        'show_v8_revision',
      ],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      'testing': {
        'platform': 'linux',
        'test_spec_file': 'chromium.memory.json',
      },
    },
    'Linux ASan LSan Tests (1)': {
      'recipe_config': 'chromium_linux_asan',
      'gclient_apply_config': [
        'v8_bleeding_edge_git',
        'chromium_lkcr',
        'show_v8_revision',
      ],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
      ],
      'parent_buildername': 'Linux ASAN Builder',
      'testing': {
        'platform': 'linux',
        'test_spec_file': 'chromium.memory.json',
      },
    },
    'Chrome Linux Perf': {
      'disable_tests': True,
      'recipe_config': 'official',
      'gclient_apply_config': [
        'perf',
        'v8_bleeding_edge_git',
        'chromium_lkcr',
        'show_v8_revision',
      ],
      'chromium_apply_config': ['chromium_perf'],
      'bot_type': 'builder_tester',
      'compile_targets': [
        'chromium_builder_perf',
      ],
      'tests': [
        steps.DynamicPerfTests(
            'release',
            'chromium-rel-linux-v8', 0, 1),
      ],
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      'testing': {
        'platform': 'linux',
      },
    },
    'Chrome Win7 Perf': {
      'disable_tests': True,
      'recipe_config': 'official',
      'gclient_apply_config': [
        'perf',
        'v8_bleeding_edge_git',
        'chromium_lkcr',
        'show_v8_revision',
      ],
      'chromium_apply_config': ['chromium_perf'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'chromium_builder_perf',
      ],
      'tests': [
        steps.DynamicPerfTests(
            'release',
            'chromium-rel-win7-dual-v8', 0, 1),
      ],
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      'testing': {
        'platform': 'win',
      },
    },
    'Chrome Mac10.6 Perf': {
      'disable_tests': True,
      'recipe_config': 'chromium',
      'gclient_apply_config': [
        'perf',
        'v8_bleeding_edge_git',
        'chromium_lkcr',
        'show_v8_revision',
      ],
      'chromium_apply_config': ['chromium_perf'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'chromium_builder_perf',
      ],
      'tests': [
        steps.DynamicPerfTests(
            'release',
            'chromium-rel-mac6-v8', 0, 1),
      ],
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      'testing': {
        'platform': 'mac',
      },
    },
  },
}
