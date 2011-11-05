# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
D = helper.Dependent
F = helper.Factory
S = helper.Scheduler

def linux(): return chromium_factory.ChromiumFactory('src/build', 'linux2')


################################################################################
## Release
################################################################################

defaults['category'] = '3webkit linux deps'

#
# Main release scheduler for chromium
#
S('s3_chromium_rel', branch='src', treeStableTimer=60)

#
# Linux Rel Builder
#
B('Webkit Linux (deps)', 'f_webkit_linux_rel', scheduler='s3_chromium_rel',
  auto_reboot=True)
F('f_webkit_linux_rel', linux().ChromiumFactory(
    tests=['test_shell', 'webkit', 'webkit_gpu', 'webkit_unit'],
    options=['--compiler=goma', 'test_shell', 'test_shell_tests',
	         'webkit_unit_tests', 'DumpRenderTree'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com'}))

def Update(config, active_master, c):
  return helper.Update(c)
