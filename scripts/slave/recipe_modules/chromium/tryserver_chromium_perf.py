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
    'win_perf_bisect_builder': chromium_perf.SPEC['builders']['Win Builder'],
    'mac_perf_bisect_builder': chromium_perf.SPEC['builders']['Mac Builder'],
  },
}

