# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-memory-archive',
  },
  'builders': {
    'Android CFI': {
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
      'bot_type': 'builder_tester',
      'testing': {'platform': 'linux'},
    },
    'Linux ASan LSan Builder': {
      'chromium_config': 'chromium_asan',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      # This doesn't affect the build, but ensures that trybots get the right
      # runtime flags.
      'chromium_apply_config': ['lsan', 'mb', 'goma_high_parallel'],
      'bot_type': 'builder',
      'testing': {'platform': 'linux'},
    },
    'Linux ASan LSan Tests (1)': {
      'chromium_config': 'chromium_asan',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      # Enable LSan at runtime. This disables the sandbox in browser tests.
      # http://crbug.com/336218
      'chromium_apply_config': ['lsan'],
      'bot_type': 'tester',
      'parent_buildername': 'Linux ASan LSan Builder',
      'testing': {'platform': 'linux'},
    },
    'Linux ASan Tests (sandboxed)': {
      'chromium_config': 'chromium_asan',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      # We want to test ASan+sandbox as well, so run browser tests again, this
      # time with LSan disabled.
      'bot_type': 'tester',
      'parent_buildername': 'Linux ASan LSan Builder',
      'testing': {'platform': 'linux'},
    },
    'Linux CFI': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'testing': {'platform': 'linux'},
    },
    'Linux MSan Builder': {
      'chromium_config': 'chromium_msan',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {'platform': 'linux'},
    },
    'Linux MSan Tests': {
      'chromium_config': 'chromium_msan',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'Linux MSan Builder',
      'testing': {'platform': 'linux'},
      'swarming_dimensions': {
        'cpu': 'x86-64',
        'os': 'Ubuntu-14.04',
      },
    },
    'Linux ChromiumOS MSan Builder': {
      'chromium_config': 'chromium_msan',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chromeos'],
      'chromium_apply_config': ['mb'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {'platform': 'linux'},
    },
    'Linux ChromiumOS MSan Tests': {
      'chromium_config': 'chromium_msan',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chromeos'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'Linux ChromiumOS MSan Builder',
      'testing': {'platform': 'linux'},
      'swarming_dimensions': {
        'cpu': 'x86-64',
        'os': 'Ubuntu-14.04',
      },
    },
    'Linux TSan Builder': {
      'chromium_config': 'chromium_tsan2',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'Linux TSan Tests': {
      'chromium_config': 'chromium_tsan2',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'Linux TSan Builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'Mac ASan 64 Builder': {
      'chromium_config': 'chromium_asan',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'chromium_apply_config': ['mb'],
      'bot_type': 'builder',
      'testing': {'platform': 'mac'},
      'checkout_dir': 'mac',
    },
    'Mac ASan 64 Tests (1)': {
      'chromium_config': 'chromium_asan',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'Mac ASan 64 Builder',
      'testing': {'platform': 'mac'},
    },
    'Linux Chromium OS ASan LSan Builder': {
      'chromium_config': 'chromium_chromiumos_asan',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chromeos'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'chromium_apply_config': ['lsan', 'mb'],
      'bot_type': 'builder',
      'testing': {'platform': 'linux'},
    },
    'Linux Chromium OS ASan LSan Tests (1)': {
      'chromium_config': 'chromium_chromiumos_asan',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chromeos'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'chromium_apply_config': ['lsan'],
      'parent_buildername': 'Linux Chromium OS ASan LSan Builder',
      'bot_type': 'tester',
      'testing': {'platform': 'linux'},
    },
    'win-asan': {
      'chromium_config': 'chromium_win_clang_asan',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'chromium_apply_config': ['mb'],
      'bot_type': 'builder_tester',
      'testing': {'platform': 'win'},
    },
  },
}
