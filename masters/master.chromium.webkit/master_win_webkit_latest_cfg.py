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

def win(): return chromium_factory.ChromiumFactory('src/webkit', 'win32')


################################################################################
## Release
################################################################################

defaults['category'] = '4webkit win latest'

# Archive location
rel_archive = master_config.GetArchiveUrl('ChromiumWebkit',
                                          'Webkit Win Builder',
                                          'webkit-win-latest-rel', 'win32')

#
# Main release schedulers for chromium and webkit
#
S('s4_chromium_rel', branch='src', treeStableTimer=60)
S('s4_webkit_rel', branch='trunk', treeStableTimer=60)

#
# Dependent schedulers for the release builder
#
D('s4_chromium_rel_dep', 's4_chromium_rel')
D('s4_webkit_rel_dep', 's4_webkit_rel')

#
# Win Rel Builder
#
B('Webkit Win Builder', 'f_webkit_win_rel',
  scheduler='s4_chromium_rel|s4_webkit_rel', builddir='webkit-win-latest-rel')
F('f_webkit_win_rel', win().ChromiumWebkitLatestFactory(slave_type='Builder'))

#
# Win Rel Webkit testers
#
B('Webkit Win', 'f_webkit_rel_tests',
  scheduler='s4_chromium_rel_dep|s4_webkit_rel_dep')
F('f_webkit_rel_tests', win().ChromiumWebkitLatestFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=['test_shell', 'webkit', 'webkit_gpu', 'webkit_unit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com'}))

################################################################################
## Debug
################################################################################

dbg_archive = master_config.GetArchiveUrl('ChromiumWebkit',
                                          'Webkit Win Builder (dbg)',
                                          'webkit-win-latest-dbg', 'win32')

#
# Main debug schedulers for chromium and webkit
#
S('s4_chromium_dbg', branch='src', treeStableTimer=60)
S('s4_webkit_dbg', branch='trunk', treeStableTimer=60)

#
# Dependent schedulers for the dbg builder
#
D('s4_chromium_dbg_dep', 's4_chromium_dbg')
D('s4_webkit_dbg_dep', 's4_webkit_dbg')

#
# Win Dbg Builder
#
B('Webkit Win Builder (dbg)', 'f_webkit_win_dbg',
  scheduler='s4_chromium_dbg|s4_webkit_dbg', builddir='webkit-win-latest-dbg')
F('f_webkit_win_dbg', win().ChromiumWebkitLatestFactory(
    target='Debug',
    slave_type='Builder'))

#
# Win Dbg Webkit testers
#

B('Webkit Win (dbg)(1)', 'f_webkit_dbg_tests_1',
  scheduler='s4_chromium_dbg_dep|s4_webkit_dbg_dep')
F('f_webkit_dbg_tests_1', win().ChromiumWebkitLatestFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['test_shell', 'webkit', 'webkit_gpu', 'webkit_unit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '1:2'}))

B('Webkit Win (dbg)(2)', 'f_webkit_dbg_tests_2',
  scheduler='s4_chromium_dbg_dep|s4_webkit_dbg_dep')
F('f_webkit_dbg_tests_2', win().ChromiumWebkitLatestFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['webkit', 'webkit_gpu'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '2:2'}))

def Update(config, active_master, c):
  return helper.Update(c)
