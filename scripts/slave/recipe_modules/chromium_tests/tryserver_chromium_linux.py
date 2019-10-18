# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


SPEC = {
  'builders': {
      'linux-layout-tests-fragment-item': {
        'chromium_config': 'chromium',
        'chromium_apply_config': ['mb'],
        'gclient_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'tests': [],
        'test_results_config': 'staging_server',
        'testing': {
          'platform': 'linux',
        },
      }
  },
}
