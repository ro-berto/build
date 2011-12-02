# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler

def linux(): return chromium_factory.ChromiumFactory('src/build', 'linux2')

################################################################################
## Release
################################################################################

#
# Main release scheduler for webkit
#
S('s6_chrome_rel', branch='src', treeStableTimer=60)
S('s6_webkit_rel', branch='trunk', treeStableTimer=60)

#
# Linux Rel Builder
#
F('f_webkit_linux_rel', linux().ChromiumWebkitLatestFactory(
    target='Release',
    tests=['devtools_perf'],
    options=['--compiler=goma', 'DumpRenderTree'],
    factory_properties={
      'perf_id': 'chromium-devtools-perf',
      'show_perf_results': True,
    }
  )
)

B('Webkit Linux 64', 'f_webkit_linux_rel', scheduler='s6_webkit_rel')

def Update(config, active_master, c):
  return helper.Update(c)
