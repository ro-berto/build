# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-v8',
  },
  'builders': {
    'Linux Debug Builder': {
      'recipe_config': 'chromium_v8',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },
  },
}
