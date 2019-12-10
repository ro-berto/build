# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-linux-archive',
  },
  'builders': {
    'fuchsia-arm64-cast': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['fuchsia_arm64'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'fuchsia',
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'fuchsia-x64-cast': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['fuchsia_x64'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'fuchsia',
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'fuchsia-x64-dbg': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['fuchsia_x64'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'fuchsia',
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'linux-gcc-rel': {
      'chromium_config': 'chromium_no_goma',
      'chromium_apply_config': [
        'mb',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'linux-ozone-rel': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [],
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',

        # This is specified because 'linux-rel' builder
        # is one of the slowest builder in CQ (crbug.com/804251).
        'goma_high_parallel',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['use_clang_coverage'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'linux-trusty-rel': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux Tests': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
        'goma_high_parallel',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['use_clang_coverage'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'Linux Builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux Builder (dbg)(32)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux Tests (dbg)(1)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'Linux Builder (dbg)',
      'testing': {
        'platform': 'linux',
      },
    },

    'Cast Audio Linux': {
      'chromium_config': 'chromium_clang',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'linux',
      },
    },
    'Cast Linux': {
      'chromium_config': 'chromium_clang',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'linux',
      },
    },

    'Fuchsia ARM64 Cast Audio': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['fuchsia_arm64'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'fuchsia',
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'Fuchsia ARM64': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['fuchsia_arm64'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'fuchsia',
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'Fuchsia x64 Cast Audio': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['fuchsia_x64'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'fuchsia',
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'Fuchsia x64': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['fuchsia_x64'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'fuchsia',
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'Leak Detection Linux': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_apply_config': [
          'mb',
        ],
      'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
      },
      'chromium_tests_apply_config': [ 'staging' ],
      'test_results_config': 'staging_server',
      'testing': {
          'platform': 'linux',
      },
    },
  },
}
