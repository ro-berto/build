# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy

from . import chromium_perf
from . import steps


def _Builders():
  # These should build with the same configs as the main perf builders.
  builders = {}

  for bisect_bot_name, perf_bot_name in _BUILDER_MAPPINGS.iteritems():
    config = copy.deepcopy(chromium_perf.SPEC['builders'][perf_bot_name])
    config['tests'] = [steps.SizesStep(None, None)]
    builders[bisect_bot_name] = config

  for bisect_bot_name, perf_bot_name in _TESTER_MAPPINGS.iteritems():
    config = copy.deepcopy(chromium_perf.SPEC['builders'][perf_bot_name])
    del config['tests']  # Don't run the same tests as the perf waterfall.
    builders[bisect_bot_name] = config

  return builders


_BUILDER_MAPPINGS = {
    'linux_perf_bisect_builder': 'Linux Builder',
    'win_perf_bisect_builder': 'Win Builder',
    'winx64_bisect_builder': 'Win x64 Builder',
    'mac_perf_bisect_builder': 'Mac Builder',
}


_TESTER_MAPPINGS = {
    'linux_perf_bisect': 'Linux Builder',
    'linux_perf_cq': 'Linux Builder',
    'linux_fyi_perf_bisect': 'Linux Builder',
    'win_perf_bisect': 'Win Builder',
    'win_8_perf_bisect': 'Win Builder',
    'winx64_10_perf_bisect': 'Win x64 Builder',
    'win_x64_perf_bisect': 'Win x64 Builder',
    'winx64ati_perf_bisect': 'Win x64 Builder',
    'winx64nvidia_perf_bisect': 'Win x64 Builder',
    'winx64intel_perf_bisect': 'Win x64 Builder',
    'winx64_zen_perf_bisect': 'Win x64 Builder',
    'winx64_10_perf_cq': 'Win x64 Builder',
    'win_fyi_perf_bisect': 'Win Builder',
    'mac_10_11_perf_bisect': 'Mac Builder',
    'mac_10_10_perf_bisect': 'Mac Builder',
    'mac_retina_perf_bisect': 'Mac Builder',
    'mac_hdd_perf_bisect': 'Mac Builder',
    'mac_retina_perf_cq': 'Mac Builder',
    'mac_fyi_perf_bisect': 'Mac Builder',
}


SPEC = {
  'settings': chromium_perf.SPEC['settings'],
  'builders': _Builders(),
}
