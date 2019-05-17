# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'builders': {
    'win32-archive-dbg': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'clobber',
        'mb',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'checkout_dir': 'win',
      'testing': {
        'platform': 'win',
      },
    },
    'win32-archive-rel': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'clobber',
        'mb',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'archive_build': True,
      'gs_bucket': 'chromium-browser-snapshots',
      'gs_build_name': 'Win',
      'gs_acl': 'public-read',
      'checkout_dir': 'win',
      'testing': {
        'platform': 'win',
      },
    },
    'win-archive-dbg': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'clobber',
        'mb',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'checkout_dir': 'win',
      'testing': {
        'platform': 'win',
      },
    },
    'win-archive-rel': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'clobber',
        'mb',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'archive_build': True,
      'gs_bucket': 'chromium-browser-snapshots',
      'gs_build_name': 'Win_x64',
      'gs_acl': 'public-read',
      'checkout_dir': 'win',
      'testing': {
        'platform': 'win',
      },
    },
    'mac-archive-dbg': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'clobber',
        'mb',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'checkout_dir': 'mac',
      'testing': {
        'platform': 'mac',
      },
    },
    'mac-archive-rel': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'clobber',
        'mb',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'archive_build': True,
      'gs_bucket': 'chromium-browser-snapshots',
      'gs_build_name': 'Mac',
      'gs_acl': 'public-read',
      'checkout_dir': 'mac',
      'testing': {
        'platform': 'mac',
      },
    },
    'linux-archive-dbg': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'clobber',
        'mb',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'checkout_dir': 'linux_clobber',
      'testing': {
        'platform': 'linux',
      },
    },
    'linux-archive-rel': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'clobber',
        'mb',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'archive_build': True,
      'gs_bucket': 'chromium-browser-snapshots',
      'gs_build_name': 'Linux_x64',
      'gs_acl': 'public-read',
      'checkout_dir': 'linux_clobber',
      'testing': {
        'platform': 'linux',
      },
    },
    'android-archive-dbg': {
      'chromium_config': 'android',
      'chromium_apply_config': [
        'clobber',
        'mb',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
        'TARGET_ARCH': 'arm',
      },
      'android_config': 'main_builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'android-archive-rel': {
      'chromium_config': 'android',
      'chromium_apply_config': [
        'clobber',
        'mb',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'android',
        'TARGET_ARCH': 'arm',
      },
      'android_config': 'main_builder',
      'archive_build': True,
      'gs_bucket': 'chromium-browser-snapshots',
      'gs_build_name': 'Android',
      'gs_acl': 'public-read',
      'testing': {
        'platform': 'linux',
      },
    },
  },
}
