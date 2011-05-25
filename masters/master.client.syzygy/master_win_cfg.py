# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import syzygy_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
D = helper.Dependent
F = helper.Factory
S = helper.Scheduler

def win():
  return syzygy_factory.SyzygyFactory('src/syzygy',
                                      target_platform='win32')

defaults['category'] = 'windows'


#
# Main Scheduler for Syzygy
#
S('syzygy_rel', branch='trunk', treeStableTimer=60)


#
# Linux Release Builder
#
B('Syzygy Windows', 'f_syzygy_win_rel', scheduler='syzygy_rel')
F('f_syzygy_win_rel', win().SyzygyFactory())


def Update(config, active_master, c):
  return helper.Update(c)
