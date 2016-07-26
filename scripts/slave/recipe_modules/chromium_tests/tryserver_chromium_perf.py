# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import chromium_perf


SPEC = {
  'builders': {},
  'settings': chromium_perf.SPEC['settings'],
}


def _AddBuildSpec(name, platform, target_bits=64):
  SPEC['builders'][name] = chromium_perf.BuildSpec(None, platform, target_bits)


def _AddTestSpec(name, platform, target_bits=64):
  # TODO(dtu): Change this to TestSpec after try job builds are all offloaded
  # to builders.
  spec = chromium_perf.BuildSpec(None, platform, target_bits)
  del spec['tests']
  SPEC['builders'][name] = spec


_AddBuildSpec('win_perf_bisect_builder', 'win', target_bits=32)
_AddBuildSpec('winx64_bisect_builder', 'win')
_AddBuildSpec('mac_perf_bisect_builder', 'mac')
_AddBuildSpec('linux_perf_bisect_builder', 'linux')


_AddTestSpec('winx64_10_perf_cq', 'win')
_AddTestSpec('mac_retina_perf_cq', 'mac')
_AddTestSpec('linux_perf_cq', 'linux')


_AddTestSpec('win_fyi_perf_bisect', 'win', target_bits=32)
_AddTestSpec('mac_fyi_perf_bisect', 'mac')
_AddTestSpec('linux_fyi_perf_bisect', 'linux')


_AddTestSpec('winx64_zen_perf_bisect', 'win')
_AddTestSpec('winx64_10_perf_bisect', 'win')
_AddTestSpec('win_8_perf_bisect', 'win', target_bits=32)
_AddTestSpec('win_perf_bisect', 'win', target_bits=32)
_AddTestSpec('win_x64_perf_bisect', 'win')
_AddTestSpec('winx64ati_perf_bisect', 'win')
_AddTestSpec('winx64intel_perf_bisect', 'win')
_AddTestSpec('winx64nvidia_perf_bisect', 'win')

_AddTestSpec('mac_10_11_perf_bisect', 'mac')
_AddTestSpec('mac_10_10_perf_bisect', 'mac')
_AddTestSpec('mac_retina_perf_bisect', 'mac')
_AddTestSpec('mac_hdd_perf_bisect', 'mac')

_AddTestSpec('linux_perf_bisect', 'linux')
