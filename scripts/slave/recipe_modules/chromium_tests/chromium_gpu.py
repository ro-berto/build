# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-gpu-archive',
    # WARNING: src-side runtest.py is only tested with chromium CQ builders.
    # Usage not covered by chromium CQ is not supported and can break
    # without notice.
    'src_side_runtest_py': True,
  },
  'builders': {
    'GPU Win Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'archive_gpu_tests',
        'chrome_with_codecs',
        'mb',
        'ninja_confirm_noop',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
      'use_isolate': True,
      'checkout_dir': 'win',
    },
    'GPU Win Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'archive_gpu_tests',
        'chrome_with_codecs',
        'mb',
        'ninja_confirm_noop',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
      'use_isolate': True,
    },
    'Win7 Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Win Builder',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'Win7 Debug (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Win Builder (dbg)',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'GPU Linux Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
        'ninja_confirm_noop',
        'archive_gpu_tests',
        'chrome_with_codecs'
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'linux',
      },
      'use_isolate': True,
      'enable_swarming': True,
      'checkout_dir': 'linux',
    },
    'GPU Linux Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
        'ninja_confirm_noop',
        'archive_gpu_tests',
        'chrome_with_codecs'
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'linux',
      },
      'use_isolate': True,
      'enable_swarming': True,
    },
    'Linux Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Linux Builder',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'Linux Debug (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Linux Builder (dbg)',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'GPU Mac Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'archive_gpu_tests',
        'chrome_with_codecs',
        'mb',
        'ninja_confirm_noop',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'mac',
      },
      'enable_swarming': True,
      'use_isolate': True,
      'checkout_dir': 'mac',
    },
    'GPU Mac Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'archive_gpu_tests',
        'chrome_with_codecs',
        'mb',
        'ninja_confirm_noop',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'mac',
      },
      'enable_swarming': True,
      'use_isolate': True,
    },
    'Mac 10.10 Release (Intel)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Mac Builder',
      'testing': {
        'platform': 'mac',
      },
      'enable_swarming': True,
    },
    'Mac 10.10 Debug (Intel)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Mac Builder (dbg)',
      'testing': {
        'platform': 'mac',
      },
      'enable_swarming': True,
    },
    'Mac 10.10 Retina Release (AMD)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Mac Builder',
      'testing': {
        'platform': 'mac',
      },
      'enable_swarming': True,
    },
    'Mac 10.10 Retina Debug (AMD)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Mac Builder (dbg)',
      'testing': {
        'platform': 'mac',
      },
      'enable_swarming': True,
    },
  },
}
