# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from . import chromium_perf
from . import steps


SPEC = {
  'settings': chromium_perf.SPEC['settings'],
  'builders': {
    # This is intended to build in the same way as the main perf builder.
    'linux_perf_bisect_builder':
        chromium_perf.SPEC['builders']['Linux Builder'],
    'win_perf_bisect_builder':
        chromium_perf.SPEC['builders']['Win Builder'],
    'win_x64_perf_bisect_builder':
        chromium_perf.SPEC['builders']['Win x64 Builder'],
    'mac_perf_bisect_builder':
        chromium_perf.SPEC['builders']['Mac Builder'],
    'linux_perf_tester':{
      'recipe_config': 'official',
      'parent_buildername': 'Linux Builder',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'compile_targets': [
        'chromium_builder_perf',
      ],
      'testing': {
        'platform': 'linux',
      },
      'tests':[steps.BisectTest()],
      'chromium_apply_config': ['chromium_perf']
    },
    'linux_perf_bisector':{
      'recipe_config': 'official',
      'parent_buildername': 'Linux Builder',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'compile_targets': [
        'chromium_builder_perf',
      ],
      'testing': {
        'platform': 'linux',
      },
      'tests':[steps.BisectTest()],
      'chromium_apply_config': ['chromium_perf']
    },
  }
}

