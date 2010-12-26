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

defaults['category'] = '7webkit linux'

#
# Main debug scheduler for src/
#
S('webkit_linux_rel', branch='src', treeStableTimer=60)

#
# Linux Rel Builder
#
B('Webkit Linux', 'webkit_linux_rel', 'compile|testers', 'webkit_linux_rel',
   builddir='webkit-linux-rel-x64')
F('webkit_linux_rel', linux().ChromiumFactory(
    tests=['webkit', 'test_shell', 'webkit_unit'],
    options=['test_shell', 'test_shell_tests', 'webkit_unit_tests',
             'DumpRenderTree'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com'}))

################################################################################
## Debug
################################################################################


dbg_archive = master_config.GetArchiveUrl('Chromium',
                                          'Webkit Linux Builder (dbg)',
                                          'webkit-linux-dbg', 'linux')

#
# Main debug scheduler for src/
#
S('webkit_linux_dbg', branch='src', treeStableTimer=60)

#
# Dependent scheduler for the dbg builder
#
D('webkit_linux_dbg_dep', 'webkit_linux_dbg')

#
# Linux Dbg Builder
#
B('Webkit Linux Builder (dbg)', 'dbg', 'compile', 'webkit_linux_dbg',
  builddir='webkit-linux-dbg')
F('dbg', linux().ChromiumFactory(
    target='Debug',
    slave_type='Builder',
    options=['test_shell', 'test_shell_tests', 'webkit_unit_tests',
             'DumpRenderTree']))

#
# Linux Dbg Unit testers
#

B('Webkit Linux Tests (dbg)(1)', 'dbg_webkit_1', 'testers',
  'webkit_linux_dbg_dep')
F('dbg_webkit_1', linux().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['webkit', 'test_shell', 'webkit_unit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '1:3'}))
  
B('Webkit Linux Tests (dbg)(2)', 'dbg_webkit_2', 'testers',
  'webkit_linux_dbg_dep')
F('dbg_webkit_2', linux().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['webkit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '2:3'}))

B('Webkit Linux Tests (dbg)(3)', 'dbg_webkit_3', 'testers',
  'webkit_linux_dbg_dep')
F('dbg_webkit_3', linux().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['webkit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '3:3'}))
  
def Update(config, active_master, c):
  return helper.Update(c)
