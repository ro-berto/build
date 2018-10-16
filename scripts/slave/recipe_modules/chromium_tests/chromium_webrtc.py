# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

SPEC = {
  'settings': { 'build_gs_bucket': 'chromium-webrtc'},
  'builders': {
    'Android Builder': {
      'android_config': 'base_config',
      'bot_type': 'builder',
      'chromium_apply_config': ['dcheck', 'mb', 'android'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_ARCH': 'arm',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android'
      },
      'gclient_apply_config': ['android'],
      'gclient_config': 'chromium_webrtc',
      'testing': { 'platform': 'linux'}
    },
    'Android Tester': {
      'android_config': 'base_config',
      'bot_type': 'tester',
      'chromium_apply_config': ['dcheck', 'mb', 'android'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_ARCH': 'arm',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android'
      },
      'gclient_apply_config': ['android'],
      'gclient_config': 'chromium_webrtc',
      'parent_buildername': 'Android Builder',
      'root_devices': True,
      'swarming_dimensions': {
        'device_os': 'MMB29Q',
        'device_type': 'bullhead',
        'os': 'Android'
      },
      'test_results_config': 'public_server',
      'testing': { 'platform': 'linux'},
    },
    'Linux Builder': {
      'bot_type': 'builder',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64
      },
      'gclient_apply_config': [],
      'gclient_config': 'chromium_webrtc',
      'testing': { 'platform': 'linux'}
    },
    'Linux Tester': {
      'bot_type': 'tester',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64
      },
      'gclient_apply_config': [ 'webrtc_test_resources'],
      'gclient_config': 'chromium_webrtc',
      'parent_buildername': 'Linux Builder',
      'test_results_config': 'public_server',
      'testing': { 'platform': 'linux'},
    },
    'Mac Builder': {
      'bot_type': 'builder',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64
      },
      'gclient_apply_config': [],
      'gclient_config': 'chromium_webrtc',
      'testing': { 'platform': 'mac'}
    },
    'Mac Tester': {
      'bot_type': 'tester',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64
      },
      'gclient_apply_config': [ 'webrtc_test_resources'],
      'gclient_config': 'chromium_webrtc',
      'parent_buildername': 'Mac Builder',
      'test_results_config': 'public_server',
      'testing': { 'platform': 'mac'},
    },
    'Mac Tester (long-running)': {
      'bot_type': 'tester',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64},
      'gclient_apply_config': [ 'webrtc_test_resources'],
      'gclient_config': 'chromium_webrtc',
      'parent_buildername': 'Mac Builder',
      'test_results_config': 'public_server',
      'testing': { 'platform': 'mac'}
    },
    'Win Builder': {
      'bot_type': 'builder',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32
      },
      'gclient_apply_config': [],
      'gclient_config': 'chromium_webrtc',
      'testing': { 'platform': 'win'}
    },
    'Win10 Tester': {
      'bot_type': 'tester',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32
      },
      'gclient_apply_config': [ 'webrtc_test_resources'],
      'gclient_config': 'chromium_webrtc',
      'parent_buildername': 'Win Builder',
      'test_results_config': 'public_server',
      'testing': { 'platform': 'win'},
    },
    'Win7 Tester': {
      'bot_type': 'tester',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32
      },
      'gclient_apply_config': [ 'webrtc_test_resources'],
      'gclient_config': 'chromium_webrtc',
      'parent_buildername': 'Win Builder',
      'test_results_config': 'public_server',
      'testing': { 'platform': 'win'},
    },
    'Win7 Tester (long-running)': {
      'bot_type': 'tester',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32
      },
      'gclient_apply_config': [ 'webrtc_test_resources'],
      'gclient_config': 'chromium_webrtc',
      'parent_buildername': 'Win Builder',
      'test_results_config': 'public_server',
      'testing': { 'platform': 'win'}
    },
    'Win8 Tester': {
      'bot_type': 'tester',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32
      },
      'gclient_apply_config': [ 'webrtc_test_resources'],
      'gclient_config': 'chromium_webrtc',
      'parent_buildername': 'Win Builder',
      'test_results_config': 'public_server',
      'testing': { 'platform': 'win'},
    }
  },
}
