# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-v8',
  },
  'builders': {
    'Chromium ASAN (symbolized)': {
      'chromium_config': 'chromium_linux_asan',
      'gclient_config': 'chromium',
      'chromium_apply_config': [
        'asan_symbolized',
        'chromium_asan_default_targets',
        'clobber',
        'sanitizer_coverage',
        'v8_verify_heap',
      ],
      'gclient_apply_config': [
        'v8_bleeding_edge_git',
        'chromium_lkgr',
        'show_v8_revision',
      ],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'cf_archive_build': True,
      'cf_gs_bucket': 'v8-asan',
      'cf_gs_acl': 'public-read',
      'cf_archive_name': 'asan-symbolized',
      'cf_revision_dir': 'v8',
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      'testing': {'platform': 'linux'},
    },
    'Chromium ASAN - debug': {
      'chromium_config': 'chromium_linux_asan',
      'gclient_config': 'chromium',
      'chromium_apply_config': [
        'chromium_asan_default_targets',
        'clobber',
        'sanitizer_coverage',
        'v8_optimize_medium',
      ],
      'gclient_apply_config': [
        'v8_bleeding_edge_git',
        'chromium_lkgr',
        'show_v8_revision',
      ],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'cf_archive_build': True,
      'cf_gs_bucket': 'v8-asan',
      'cf_gs_acl': 'public-read',
      'cf_archive_name': 'asan',
      'cf_revision_dir': 'v8',
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      'testing': {'platform': 'linux'},
    },
    'Chromium ASAN arm64 - debug': {
      'chromium_config': 'chromium_linux_asan',
      'gclient_config': 'chromium',
      'chromium_apply_config': [
        'clobber',
        'sanitizer_coverage',
        'v8_arch_arm',        
        'v8_d8_default_target',
        'v8_optimize_medium',
      ],
      'gclient_apply_config': [
        'v8_bleeding_edge_git',
        'chromium_lkgr',
        'show_v8_revision',
      ],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'cf_archive_build': True,
      'cf_gs_bucket': 'v8-asan',
      'cf_gs_acl': 'public-read',
      'cf_archive_name': 'arm64-asan',
      'cf_revision_dir': 'v8',
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      'testing': {'platform': 'linux'},
    },
    'Chromium ASAN mipsel - debug': {
      'chromium_config': 'chromium_linux_asan',
      'gclient_config': 'chromium',
      'chromium_apply_config': [
        'clobber',
        'sanitizer_coverage',
        'v8_arch_mipsel',        
        'v8_d8_default_target',
        'v8_optimize_medium',
      ],
      'gclient_apply_config': [
        'v8_bleeding_edge_git',
        'chromium_lkgr',
        'show_v8_revision',
      ],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder',
      'cf_archive_build': True,
      'cf_gs_bucket': 'v8-asan',
      'cf_gs_acl': 'public-read',
      'cf_archive_name': 'mipsel-asan',
      'cf_revision_dir': 'v8',
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      'testing': {'platform': 'linux'},
    },
  },
}
