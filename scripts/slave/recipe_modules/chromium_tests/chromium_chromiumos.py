# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-chromiumos-archive',
    # WARNING: src-side runtest.py is only tested with chromium CQ builders.
    # Usage not covered by chromium CQ is not supported and can break
    # without notice.
    'src_side_runtest_py': True,
  },
  'builders': {
    'Linux ChromiumOS Full': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['chromeos', 'mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'app_list_unittests',
        'base_unittests',
        'browser_tests',
        'cacheinvalidation_unittests',
        'chromeos_unittests',
        'components_unittests',
        'compositor_unittests',
        'content_browsertests',
        'content_unittests',
        'crypto_unittests',
        'dbus_unittests',
        'device_unittests',
        'gcm_unit_tests',
        'google_apis_unittests',
        'gpu_unittests',
        'interactive_ui_tests',
        'ipc_tests',
        'jingle_unittests',
        'media_unittests',
        'message_center_unittests',
        'nacl_loader_unittests',
        'net_unittests',
        'ppapi_unittests',
        'printing_unittests',
        'remoting_unittests',
        'sandbox_linux_unittests',
        'sql_unittests',
        'ui_base_unittests',
        'unit_tests',
        'url_unittests',
        'views_unittests',
      ],
      'tests': [
        steps.ArchiveBuildStep(
            'chromium-browser-snapshots',
            gs_acl='public-read',
        ),
      ],
      'testing': {
        'platform': 'linux',
      },
    },

    'Linux ChromiumOS Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['chromeos', 'ninja_confirm_noop', 'mb'],
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
      'enable_swarming': True,
      'checkout_dir': 'linux_chromeos',
    },
    'Linux ChromiumOS Tests (1)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['chromeos', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'Linux ChromiumOS Builder',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'Linux ChromiumOS Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['chromeos', 'mb', 'ninja_confirm_noop'],
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
      'enable_swarming': True,
      'checkout_dir': 'linux_chromeos',
    },
    'Linux ChromiumOS Tests (dbg)(1)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['chromeos', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'Linux ChromiumOS Builder (dbg)',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },
  },
}

# Simple Chrome compile-only builders.
for board in ('amd64-generic', 'daisy'):
  SPEC['builders']['ChromiumOS %s Compile' % (board,)] = {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['chromeos', 'mb', 'ninja_confirm_noop'],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_PLATFORM': 'chromeos',
      'TARGET_CROS_BOARD': board,
    },
    'bot_type': 'builder',
    'compile_targets': [
      'chromiumos_preflight',
    ],
    'testing': {
      'platform': 'linux',
    },
  }


def _config(name,
            cros_board=None,
            target_arch='intel',
            target_bits=64
           ):
  build_config = 'Release' if '-rel' in name else 'Debug'
  cfg = {
    'chromium_config': 'chromium',
    'chromium_apply_config': [
      'chromeos', 'mb', 'ninja_confirm_noop',
    ],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': build_config,
      'TARGET_ARCH': target_arch,
      'TARGET_BITS': target_bits,
    },
    'bot_type': 'builder_tester',
    'testing': {
      'platform': 'linux',
    },
    'tests': {},
    'enable_swarming': True,
  }
  if cros_board:
    cfg['chromium_config_kwargs']['TARGET_CROS_BOARD'] = cros_board
    cfg['chromium_config_kwargs']['TARGET_PLATFORM'] = 'chromeos'
  return name, cfg


SPEC['builders'].update([
    _config('linux-chromeos-rel'),
    _config('linux-chromeos-dbg'),
    _config('chromeos-amd64-generic-rel', cros_board='amd64-generic'),
    _config('chromeos-daisy-rel', cros_board='daisy',
            target_arch='arm', target_bits=32),
])
