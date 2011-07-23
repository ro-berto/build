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

defaults['category'] = '6webkit linux latest'

#
# Main release scheduler for webkit
#
S('s6_webkit_rel', branch='trunk', treeStableTimer=60)

#
# Linux Rel Builder
#
B('Webkit Linux', 'f_webkit_linux_rel', scheduler='s6_webkit_rel')
F('f_webkit_linux_rel', linux().ChromiumWebkitLatestFactory(
    tests=['test_shell', 'webkit', 'webkit_gpu', 'webkit_unit'],
    options=['--compiler=goma', 'test_shell', 'test_shell_tests',
             'webkit_unit_tests', 'DumpRenderTree'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com'}))

B('Webkit Linux 32', 'f_webkit_linux_rel', scheduler='s6_webkit_rel')

################################################################################
## Debug
################################################################################

#
# Main debug scheduler for webkit
#
S('s6_webkit_dbg', branch='trunk', treeStableTimer=60)

#
# Linux Dbg Webkit testers
#

B('Webkit Linux (dbg)(1)', 'f_webkit_dbg_tests_1', scheduler='s6_webkit_dbg')
F('f_webkit_dbg_tests_1', linux().ChromiumWebkitLatestFactory(
    target='Debug',
    tests=['test_shell', 'webkit', 'webkit_gpu', 'webkit_unit'],
    options=['--compiler=goma', 'test_shell', 'test_shell_tests',
             'webkit_unit_tests', 'DumpRenderTree'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '1:2'}))

B('Webkit Linux (dbg)(2)', 'f_webkit_dbg_tests_2', scheduler='s6_webkit_dbg')
F('f_webkit_dbg_tests_2', linux().ChromiumWebkitLatestFactory(
    target='Debug',
    tests=['webkit', 'webkit_gpu'],
    options=['--compiler=goma', 'test_shell', 'DumpRenderTree'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '2:2'}))

def Update(config, active_master, c):
  return helper.Update(c)
