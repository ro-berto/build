# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

RESULTS_URL = 'https://chromeperf.appspot.com'

SPEC = {
  'builders': {
    'Linux x64': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'clobber',
        'isolation_mode_noop',
        'mb',
        'ninja_confirm_noop',
        'no_dump_symbols',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'all',
      ],
      'tests': [
        steps.SizesStep(RESULTS_URL, 'chromium-rel-linux-64'),
      ],
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'archive_build': True,
      'gs_bucket': 'chromium-browser-snapshots',
      'gs_acl': 'public-read',
      'testing': {
        'platform': 'linux',
      },
    },
  },
}
