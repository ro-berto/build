# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import omaha_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler

def win(): return omaha_factory.OmahaFactory('win32')


################################################################################
## Release
################################################################################

defaults['category'] = '1windows'

# Main debug scheduler for src/
#
S('win_rel', branch='trunk', treeStableTimer=60)

#
# Win Rel Builder
#
B('Win Release', 'rel', 'compile|windows', 'win_rel', notify_on_missing=True)
F('rel', win().OmahaFactory())


def Update(config, active_master, c):
  return helper.Update(c)
