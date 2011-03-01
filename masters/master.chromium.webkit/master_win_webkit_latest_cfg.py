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

def win(): return chromium_factory.ChromiumFactory('src/webkit', 'win32')


################################################################################
## Release
################################################################################

defaults['category'] = '4webkit win latest'

#
# Main release scheduler for webkit
#
S('s4_webkit_rel', branch='trunk', treeStableTimer=60)

#
# Win Rel Builder
#
B('Webkit Win Builder', 'f_webkit_win_rel', scheduler='s4_webkit_rel',
  builddir='webkit-win-latest-rel')
F('f_webkit_win_rel', win().ChromiumWebkitLatestFactory(slave_type='Builder'))

#
# Win Rel Webkit testers
#
B('Webkit Win', 'f_webkit_rel_tests', scheduler='s4_webkit_rel')
F('f_webkit_rel_tests', win().ChromiumWebkitLatestFactory(
    tests=['test_shell', 'webkit', 'webkit_gpu', 'webkit_unit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com'}))

B('Webkit Vista', 'f_webkit_rel_tests', scheduler='s4_webkit_rel')

B('Webkit Win7', 'f_webkit_rel_tests', scheduler='s4_webkit_rel')

################################################################################
## Debug
################################################################################

#
# Main debug scheduler for webkit
#
S('s4_webkit_dbg', branch='trunk', treeStableTimer=60)

#
# Win Dbg Builder
#
B('Webkit Win Builder (dbg)', 'f_webkit_win_dbg', scheduler='s4_webkit_dbg',
  builddir='webkit-win-latest-dbg')
F('f_webkit_win_dbg', win().ChromiumWebkitLatestFactory(
    target='Debug',
    slave_type='Builder'))

#
# Win Dbg Webkit testers
#

B('Webkit Win (dbg)(1)', 'f_webkit_dbg_tests_1', scheduler='s4_webkit_dbg')
F('f_webkit_dbg_tests_1', win().ChromiumWebkitLatestFactory(
    target='Debug',
    tests=['test_shell', 'webkit', 'webkit_gpu', 'webkit_unit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '1:2'}))

B('Webkit Win (dbg)(2)', 'f_webkit_dbg_tests_2', scheduler='s4_webkit_dbg')
F('f_webkit_dbg_tests_2', win().ChromiumWebkitLatestFactory(
    target='Debug',
    tests=['webkit', 'webkit_gpu'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '2:2'}))

def Update(config, active_master, c):
  return helper.Update(c)
