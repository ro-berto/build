# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler
T = helper.Triggerable

def win(): return chromium_factory.ChromiumFactory('src/build', 'win32')

defaults['category'] = '4webkit win latest'

webkit_tests = [
  'test_shell',
  'webkit',
  'webkit_lint',
  'webkit_unit',
]

################################################################################
## Release
################################################################################

# Archive location
rel_archive = master_config.GetArchiveUrl('ChromiumWebkit',
                                          'Webkit Win Builder',
                                          'webkit-win-latest-rel', 'win32')
#
# Main release scheduler for webkit
#
S('s4_webkit_rel', branch='trunk', treeStableTimer=60)

#
# Triggerable scheduler for testers
#
T('s4_webkit_rel_trigger')

#
# Win Rel Builder
#
B('Webkit Win Builder', 'f_webkit_win_rel', scheduler='s4_webkit_rel',
  builddir='webkit-win-latest-rel')
F('f_webkit_win_rel', win().ChromiumWebkitLatestFactory(
    slave_type='Builder',
    project='all.sln;webkit_builder_win',
    factory_properties={
        'trigger': 's4_webkit_rel_trigger',
    }))

#
# Win Rel Webkit testers
#
B('Webkit Win', 'f_webkit_rel_tests', scheduler='s4_webkit_rel_trigger',
  auto_reboot=True)
F('f_webkit_rel_tests', win().ChromiumWebkitLatestFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=webkit_tests,
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com'}))

B('Webkit Win7', 'f_webkit_rel_tests', scheduler='s4_webkit_rel_trigger',
  auto_reboot=True)

################################################################################
## Debug
################################################################################

# Archive location
dbg_archive = master_config.GetArchiveUrl('ChromiumWebkit',
                                          'Webkit Win Builder (dbg)',
                                          'webkit-win-latest-dbg', 'win32')
#
# Main debug scheduler for webkit
#
S('s4_webkit_dbg', branch='trunk', treeStableTimer=60)

#
# Triggerable scheduler for testers
#
T('s4_webkit_dbg_trigger')

#
# Win Dbg Builder
#
B('Webkit Win Builder (dbg)', 'f_webkit_win_dbg', scheduler='s4_webkit_dbg',
  builddir='webkit-win-latest-dbg')
F('f_webkit_win_dbg', win().ChromiumWebkitLatestFactory(
    target='Debug',
    slave_type='Builder',
    project='all.sln;webkit_builder_win',
    factory_properties={
        'trigger': 's4_webkit_dbg_trigger',
    }))

#
# Win Dbg Webkit testers
#

B('Webkit Win (dbg)(1)', 'f_webkit_dbg_tests_1',
    scheduler='s4_webkit_dbg_trigger', auto_reboot=True)
F('f_webkit_dbg_tests_1', win().ChromiumWebkitLatestFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=webkit_tests,
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '1:2'}))

B('Webkit Win (dbg)(2)', 'f_webkit_dbg_tests_2',
    scheduler='s4_webkit_dbg_trigger', auto_reboot=True)
F('f_webkit_dbg_tests_2', win().ChromiumWebkitLatestFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['webkit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '2:2'}))

def Update(config, active_master, c):
  return helper.Update(c)
