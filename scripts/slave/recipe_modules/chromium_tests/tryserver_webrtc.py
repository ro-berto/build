# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

SPEC = {
  'settings': { 'luci_project': 'webrtc'},
  'builders': {
    'android_chromium_compile': {
      'android_config': 'base_config',
      'bot_type': 'builder',
      'chromium_apply_config': [ 'dcheck', 'mb', 'android'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_ARCH': 'arm',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android'
      },
      'gclient_apply_config': [ 'android'],
      'gclient_config': 'chromium_no_telemetry_dependencies',
      'testing': { 'platform': 'linux'}},
    'linux_chromium_compile': {
      'bot_type': 'builder',
      'chromium_apply_config': [ 'dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64
      },
      'gclient_apply_config': [],
      'gclient_config': 'chromium_no_telemetry_dependencies',
      'testing': { 'platform': 'linux'}
    },
    'mac_chromium_compile': {
      'bot_type': 'builder',
      'chromium_apply_config': [ 'dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64
      },
      'gclient_apply_config': [],
      'gclient_config': 'chromium_no_telemetry_dependencies',
      'testing': { 'platform': 'mac'}
    },
    'win_chromium_compile': {
      'bot_type': 'builder',
      'chromium_apply_config': [ 'dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release', 'TARGET_BITS': 64
      },
      'gclient_apply_config': [],
      'gclient_config': 'chromium_no_telemetry_dependencies',
      'testing': { 'platform': 'win'}
    }
  },
}
