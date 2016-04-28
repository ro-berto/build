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
    'linux_perf_bisect':
        chromium_perf.SPEC['builders']['Linux Builder'],
    'linux_perf_cq':
        chromium_perf.SPEC['builders']['Linux Builder'],
    'linux_fyi_perf_bisect':
        chromium_perf.SPEC['builders']['Linux Builder'],
    'win_perf_bisect_builder':
        chromium_perf.SPEC['builders']['Win Builder'],
    'win_perf_bisect':
        chromium_perf.SPEC['builders']['Win Builder'],
    'win_8_perf_bisect':
        chromium_perf.SPEC['builders']['Win Builder'],
    'winx64_10_perf_bisect':
        chromium_perf.SPEC['builders']['Win x64 Builder'],
    'winx64_bisect_builder':
        chromium_perf.SPEC['builders']['Win x64 Builder'],
    'win_x64_perf_bisect':
        chromium_perf.SPEC['builders']['Win x64 Builder'],
    'winx64ati_perf_bisect':
        chromium_perf.SPEC['builders']['Win x64 Builder'],
    'winx64nvidia_perf_bisect':
        chromium_perf.SPEC['builders']['Win x64 Builder'],
    'winx64intel_perf_bisect':
        chromium_perf.SPEC['builders']['Win x64 Builder'],
    'winx64_zen_perf_bisect':
        chromium_perf.SPEC['builders']['Win x64 Builder'],
    'winx64_10_perf_cq':
        chromium_perf.SPEC['builders']['Win x64 Builder'],
    'win_fyi_perf_bisect':
        chromium_perf.SPEC['builders']['Win Builder'],
    'mac_perf_bisect_builder':
        chromium_perf.SPEC['builders']['Mac Builder'],
    'mac_10_11_perf_bisect':
        chromium_perf.SPEC['builders']['Mac Builder'],
    'mac_10_10_perf_bisect':
        chromium_perf.SPEC['builders']['Mac Builder'],
    'mac_retina_perf_bisect':
        chromium_perf.SPEC['builders']['Mac Builder'],
    'mac_hdd_perf_bisect':
        chromium_perf.SPEC['builders']['Mac Builder'],
    'mac_retina_perf_cq':
        chromium_perf.SPEC['builders']['Mac Builder'],
    'mac_fyi_perf_bisect':
        chromium_perf.SPEC['builders']['Mac Builder'],
  }
}

