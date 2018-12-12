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
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['fuchsia'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'fuchsia',
      },
      'bot_type': 'builder',
      'checkout_dir': 'linux',
      'testing': {
        'platform': 'linux',
      },
    },
    'fuchsia-x64-cast': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['fuchsia'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'fuchsia',
      },
      'bot_type': 'builder',
      'checkout_dir': 'linux',
      'testing': {
        'platform': 'linux',
      },
    },
    'linux-gcc-rel': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
        'ninja_confirm_noop',
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
      'checkout_dir': 'linux',
    },
    # This is not a real bot; it isn't actually present on the waterfall. It's
    # only here to be mirrored by a trybot which needs a special config
    # (goma_rbe_staging).
    'linux-goma-rbe-staging-rel': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
        'ninja_confirm_noop',
        'goma_rbe_staging',
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
      'checkout_dir': 'linux',
    },
    'linux-jumbo-rel': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_apply_config': [
          'mb',
          'ninja_confirm_noop',
      ],
      'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
      },
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
      'checkout_dir': 'linux',
      'testing': {
        'platform': 'linux',
      },
    },
    'linux-xenial-rel': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'checkout_dir': 'linux',
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
        'ninja_confirm_noop',

        # This is specified because 'linux_chromium_rel_ng' builder
        # is one of the slowest builder in CQ (crbug.com/804251).
        'goma_high_parallel',
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
      # 5% of the linux_chromium_rel_ng builds will use exparchive instead of
      # batcharchive to allow comparison of performance.
      'force_exparchive': 5,
      'checkout_dir': 'linux',
    },
    'Linux Tests': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
        'ninja_confirm_noop',
        'goma_high_parallel',
      ],
      'gclient_config': 'chromium',
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
        'ninja_confirm_noop',
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
      'checkout_dir': 'linux',
    },
    'Linux Tests (dbg)(1)(32)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'Linux Builder (dbg)(32)',
      'testing': {
        'platform': 'linux',
      },
    },

    'Linux Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
        'ninja_confirm_noop',
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
      'checkout_dir': 'linux',
    },
    'Linux Tests (dbg)(1)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
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
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
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
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
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
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['fuchsia'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'fuchsia',
      },
      'bot_type': 'builder',
      'checkout_dir': 'linux',
      'testing': {
        'platform': 'linux',
      },
    },
    'Fuchsia ARM64': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['fuchsia'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'fuchsia',
      },
      'bot_type': 'builder',
      'checkout_dir': 'linux',
      'testing': {
        'platform': 'linux',
      },
    },
    'Fuchsia x64 Cast Audio': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['fuchsia'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'fuchsia',
      },
      'bot_type': 'builder',
      'checkout_dir': 'linux',
      'testing': {
        'platform': 'linux',
      },
    },
    'Fuchsia x64': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['fuchsia'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'fuchsia',
      },
      'bot_type': 'builder',
      'checkout_dir': 'linux',
      'testing': {
        'platform': 'linux',
      },
    },
    'Leak Detection Linux': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_apply_config': [
          'mb',
          'ninja_confirm_noop',
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
