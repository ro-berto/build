# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


SPEC = {
  'builders': {
    'android_blink_rel': {
      'android_config': 'main_builder',
      'chromium_apply_config': [
        'mb',
        'ninja_confirm_noop',
      ],
      'chromium_config': 'android',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
    },
  },
}
