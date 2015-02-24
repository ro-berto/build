# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy

from . import chromium_chromiumos
from . import steps

SPEC = copy.deepcopy(chromium_chromiumos.SPEC)

SPEC['settings']['build_gs_bucket'] = 'chromium-webkit-archive'

SPEC['builders'].update({
  'WebKit Linux': {
    'recipe_config': 'chromium',
    'set_component_rev': {'name': 'src/third_party/WebKit', 'rev_str': '%s'},
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 64,
    },
    'compile_targets': [
      'blink_tests',
    ],
    'test_generators': [
      steps.generate_gtest,
      steps.generate_script,
    ],
    'testing': {
      'platform': 'linux',
    },
    'enable_swarming': True,
    'use_isolate': True,
  },
})

for b in SPEC['builders'].itervalues():
    b['gclient_apply_config'] = ['blink']
