# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

SPEC = {
  'builders': {
    'Chromeos Builder': {
      'recipe_config': 'chrome_chromeos',
      'testing': {
        'platform': 'linux',
      },
    },
    'Release Buildspec Builder': {
      'recipe_config': 'chrome_chromeos_buildspec',
      'buildspec_version': '1.2.3.4',
      'testing': {
        'platform': 'linux',
      },
    },
  },
}
