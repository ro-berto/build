# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


SPEC = {
  'builders': {
    'linux-coverage-rel': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
        'ninja_confirm_noop',
        'goma_high_parallel',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['use_clang_coverage'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'chromium_tests_apply_config': [
          'code_coverage_trybot',
      ],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
      'checkout_dir': 'linux',
    },
  },
}
