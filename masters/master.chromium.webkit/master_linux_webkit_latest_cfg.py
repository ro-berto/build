# Copyright (c) 2010 The Chromium Authors. All rights reserved.
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

defaults['category'] = '6webkit linux latest'

#
# Main release scheduler for chromium and webkit
#
S('s6_chromium_rel', branch='src', treeStableTimer=60)
S('s6_webkit_rel', branch='trunk', treeStableTimer=60)

#
# Linux Rel Builder
#
B('Webkit Linux', 'f_webkit_linux_rel',
  scheduler='s6_chromium_rel|s6_webkit_rel')
F('f_webkit_linux_rel', linux().ChromiumWebkitLatestFactory(
    tests=['test_shell', 'webkit', 'webkit_gpu', 'webkit_unit'],
    options=['test_shell', 'test_shell_tests', 'webkit_unit_tests',
             'DumpRenderTree'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com'}))

################################################################################
## Debug
################################################################################

dbg_archive = master_config.GetArchiveUrl('ChromiumWebkit',
                                          'Webkit Linux Builder (dbg)',
                                          'webkit-linux-latest-dbg', 'linux')

#
# Main debug schedulers for chromium and webkit
#
S('s6_chromium_dbg', branch='src', treeStableTimer=60)
S('s6_webkit_dbg', branch='trunk', treeStableTimer=60)

#
# Dependent schedulers for the dbg builder
#
D('s6_chromium_dbg_dep', 's6_chromium_dbg')
D('s6_webkit_dbg_dep', 's6_webkit_dbg')

#
# Linux Dbg Builder
#
B('Webkit Linux Builder (dbg)', 'f_webkit_linux_dbg',
  scheduler='s6_chromium_dbg|s6_webkit_dbg', builddir='webkit-linux-latest-dbg')
F('f_webkit_linux_dbg', linux().ChromiumWebkitLatestFactory(
    target='Debug',
    slave_type='Builder',
    options=['test_shell', 'test_shell_tests', 'webkit_unit_tests',
             'DumpRenderTree']))

#
# Linux Dbg Webkit testers
#

B('Webkit Linux (dbg)(1)', 'f_webkit_dbg_tests_1',
  scheduler='s6_chromium_dbg_dep|s6_webkit_dbg_dep')
F('f_webkit_dbg_tests_1', linux().ChromiumWebkitLatestFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['test_shell', 'webkit', 'webkit_gpu', 'webkit_unit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '1:2'}))

B('Webkit Linux (dbg)(2)', 'f_webkit_dbg_tests_2',
  scheduler='s6_chromium_dbg_dep|s6_webkit_dbg_dep')
F('f_webkit_dbg_tests_2', linux().ChromiumWebkitLatestFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['webkit', 'webkit_gpu'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '2:2'}))

def Update(config, active_master, c):
  return helper.Update(c)
