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

defaults['category'] = '3webkit linux pinned'

#
# Main release scheduler for chromium
#
S('s3_chromium_rel', branch='src', treeStableTimer=60)

#
# Linux Rel Builder
#
B('Webkit Linux (deps)', 'f_webkit_linux_rel', scheduler='s3_chromium_rel')
F('f_webkit_linux_rel', linux().ChromiumFactory(
    tests=['test_shell', 'webkit', 'webkit_unit'],
    options=['test_shell', 'test_shell_tests', 'webkit_unit_tests',
             'DumpRenderTree'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com'}))

################################################################################
## Debug
################################################################################

dbg_archive = master_config.GetArchiveUrl('ChromiumWebkit',
                                          'Webkit Linux Builder (deps)(dbg)',
                                          'webkit-linux-pinned-dbg', 'linux')

#
# Main debug scheduler for chromium
#
S('s3_chromium_dbg', branch='src', treeStableTimer=60)

#
# Dependent scheduler for the dbg builder
#
D('s3_chromium_dbg_dep', 's3_chromium_dbg')

#
# Linux Dbg Builder
#
B('Webkit Linux Builder (deps)(dbg)', 'f_webkit_linux_dbg',
  scheduler='s3_chromium_dbg', builddir='webkit-linux-pinned-dbg')
F('f_webkit_linux_dbg', linux().ChromiumFactory(
    target='Debug',
    slave_type='Builder',
    options=['test_shell', 'test_shell_tests', 'webkit_unit_tests',
             'DumpRenderTree']))

#
# Linux Dbg Webkit testers
#

B('Webkit Linux (deps)(dbg)(1)', 'f_webkit_dbg_tests_1',
  scheduler='s3_chromium_dbg_dep')
F('f_webkit_dbg_tests_1', linux().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['test_shell', 'webkit', 'webkit_unit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '1:2'}))

B('Webkit Linux (deps)(dbg)(2)', 'f_webkit_dbg_tests_2',
  scheduler='s3_chromium_dbg_dep')
F('f_webkit_dbg_tests_2', linux().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['webkit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '2:2'}))

def Update(config, active_master, c):
  return helper.Update(c)
