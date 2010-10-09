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

defaults['category'] = '5webkit win'

# Archive location
rel_archive = master_config.GetArchiveUrl('Chromium', 'Webkit Win Builder',
                                          'webkit-win-rel', 'win32')

#
# Main debug scheduler for src/
#
S('webkit_win_rel', branch='src', treeStableTimer=60)

#
# Dependent scheduler for the dbg builder
#
D('webkit_win_rel_dep', 'webkit_win_rel')

#
# Win Rel Builder
#
B('Webkit Win Builder', 'webkit_win_rel', 'compile', 'webkit_win_rel',
  builddir='webkit-win-rel')
F('webkit_win_rel', win().ChromiumFactory(
    'webkit-win-rel',
    slave_type='Builder'))

#
# Win Rel Webkit testers
#
B('Webkit Win', 'webkit_rel_tests', 'testers', 'webkit_win_rel_dep')
F('webkit_rel_tests', win().ChromiumFactory(
    'webkit-win-rel',
    slave_type='Tester',
    build_url=rel_archive,
    tests=['test_shell', 'webkit', 'webkit_unit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com'}))

################################################################################
## Debug
################################################################################

dbg_archive = master_config.GetArchiveUrl('Chromium',
                                          'Webkit Win Builder (dbg)',
                                          'webkit-win-dbg', 'win32')

#
# Main debug scheduler for src/
#
S('webkit_win_dbg', branch='src', treeStableTimer=60)

#
# Dependent scheduler for the dbg builder
#
D('webkit_win_dbg_dep', 'webkit_win_dbg')

#
# Win Dbg Builder
#
B('Webkit Win Builder (dbg)', 'webkit_win_dbg', 'compile', 'webkit_win_dbg',
  builddir='webkit-win-dbg')
F('webkit_win_dbg', win().ChromiumFactory(
    'webkit-win-dbg',
    target='Debug',
    slave_type='Builder'))

#
# Win Dbg Webkit testers.
#

B('Webkit Win (dbg)(1)', 'webkit_dbg_tests_1', 'testers', 'webkit_win_rel_dep')
F('webkit_dbg_tests_1', win().ChromiumFactory(
    'webkit-win-dbg',
    slave_type='Tester',
    target='Debug',
    build_url=dbg_archive,
    tests=['webkit', 'test_shell', 'webkit_unit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '1:3'}))

B('Webkit Win (dbg)(2)', 'webkit_dbg_tests_2', 'testers', 'webkit_win_rel_dep')
F('webkit_dbg_tests_2', win().ChromiumFactory(
    'webkit-win-dbg',
    slave_type='Tester',
    target='Debug',
    build_url=dbg_archive,
    tests=['webkit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '2:3'}))

B('Webkit Win (dbg)(3)', 'webkit_dbg_tests_3', 'testers', 'webkit_win_rel_dep')
F('webkit_dbg_tests_3', win().ChromiumFactory(
    'webkit-win-dbg',
    slave_type='Tester',
    target='Debug',
    build_url=dbg_archive,
    tests=['webkit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '3:3'}))

def Update(config, active_master, c):
  return helper.Update(c)
