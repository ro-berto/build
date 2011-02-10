# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import skia_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
D = helper.Dependent
F = helper.Factory
S = helper.Scheduler

def linux(): return skia_factory.SkiaFactory('trunk', target_platform='linux')


defaults['category'] = 'linux'


#
# Main Scheduler for Skia
#
S('skia_rel', branch='trunk', treeStableTimer=60)


#
# Linux Release Builder
#
B('Skia Linux', 'f_skia_linux_rel', scheduler='skia_rel')
F('f_skia_linux_rel', linux().SkiaFactory()) 


def Update(config, active_master, c):
  return helper.Update(c)
