# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import logging
import sys

from common.slave_alloc import SlaveAllocator
from common.cros_chromite import Get, ChromiteTarget
from master.cros import builder_config


# Declare a slave allocator. We do this here so we can access the slaves
# configured by 'slaves.cfg' in 'master.cfg'.
slave_allocator = SlaveAllocator()


# Get the pinned Chromite configuration.
cbb_config = Get(allow_fetch=True)


# Select any board that is configured to build on this waterfall.
def _GetWaterfallTargets():
  result = collections.OrderedDict()
  for config in cbb_config.itervalues():
    if config.get('active_waterfall') != 'chromiumos':
      continue
    result[config.name] = config
  return result
waterfall_targets = _GetWaterfallTargets()


# Load the builder configs.
builder_configs = builder_config.GetBuilderConfigs(waterfall_targets)
builder_name_map = dict((c.builder_name, c)
                        for c in builder_configs.itervalues())
