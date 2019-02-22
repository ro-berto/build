# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'builders': {
    'Chromium Linux Goma Staging': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_staging', 'clobber', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Mac Goma Staging': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_staging', 'clobber', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'mac',
      },
    },
    'CrWinGomaStaging': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_staging', 'clobber', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'win',
      },
    },
    'Chromium Linux Goma RBE ToT': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_rbe_tot', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Linux Goma RBE ToT (ATS)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'goma_arbitrary_toolchain_support', 'goma_rbe_tot', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Linux Goma RBE Staging (clobber)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_mixer_staging', 'clobber', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Linux Goma RBE Staging': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_mixer_staging', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Linux Goma RBE Staging (dbg) (clobber)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_mixer_staging', 'clobber', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Linux Goma RBE Staging (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_mixer_staging', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Linux Goma RBE Prod': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_rbe_prod', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Linux Goma RBE Prod (clobber)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_rbe_prod', 'clobber', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Linux Goma RBE Prod (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_rbe_prod', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Linux Goma RBE Prod (dbg) (clobber)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_rbe_prod', 'clobber', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Mac Goma RBE Staging': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_mixer_staging', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'mac',
      },
    },
    'Chromium Mac Goma RBE Staging (clobber)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_mixer_staging', 'clobber', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'mac',
      },
    },
    'Chromium Mac Goma RBE Staging (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_mixer_staging', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'mac',
      },
    },
    'Chromium Android ARM 32-bit Goma RBE ToT': {
      'chromium_config': 'android',
      'chromium_apply_config': ['goma_rbe_tot'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder_mb',
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Android ARM 32-bit Goma RBE Staging': {
      'chromium_config': 'android',
      'chromium_apply_config': ['goma_mixer_staging'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder_mb',
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Android ARM 32-bit Goma RBE Prod': {
      'chromium_config': 'android',
      'chromium_apply_config': ['goma_rbe_prod'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder_mb',
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Android ARM 32-bit Goma RBE Prod (clobber)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['goma_rbe_prod', 'clobber'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder_mb',
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Android ARM 32-bit Goma RBE Prod (dbg)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['goma_rbe_prod'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder_mb',
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Android ARM 32-bit Goma RBE Prod (dbg) (clobber)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['goma_rbe_prod', 'clobber'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder_mb',
      'testing': {
        'platform': 'linux',
      },
    },
    'Chromium Win Goma RBE ToT': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'goma_rbe_tot', 'goma_arbitrary_toolchain_support', 'mb'
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'win',
      },
    },
    'Chromium Win Goma RBE Staging': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'goma_mixer_staging', 'goma_arbitrary_toolchain_support', 'mb'
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'win',
      },
    },
    'Chromium Win Goma RBE Staging (clobber)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'clobber', 'goma_mixer_staging', 'goma_arbitrary_toolchain_support',
        'mb',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'win',
      },
    },
    'Chromium Win Goma RBE Prod': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'goma_rbe_prod', 'goma_arbitrary_toolchain_support', 'mb'
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'win',
      },
    },
    'Chromium Win Goma RBE Prod (clobber)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'clobber', 'goma_rbe_prod', 'goma_arbitrary_toolchain_support', 'mb',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'win',
      },
    },
    'Chromium Win Goma RBE Prod (dbg) ': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'goma_rbe_prod', 'goma_arbitrary_toolchain_support', 'mb'
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'win',
      },
    },
    'Chromium Win Goma RBE Prod (dbg) (clobber)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'clobber', 'goma_rbe_prod', 'goma_arbitrary_toolchain_support', 'mb',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'testing': {
        'platform': 'win',
      },
    },
  },
}
