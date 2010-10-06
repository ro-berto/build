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

def mac(): return chromium_factory.ChromiumFactory('src/build', 'darwin')


################################################################################
## Release
################################################################################

defaults['category'] = '9webkit mac'

# Archive location
rel_archive = master_config.GetArchiveUrl('Chromium', 'Webkit Mac Builder',
                                          'webkit-mac-rel', 'mac')

#
# Main debug scheduler for src/
#
S('webkit_mac_rel', branch='src', treeStableTimer=60)

#
# Dependent scheduler for the dbg builder
#
D('webkit_mac_rel_dep', 'webkit_mac_rel')

#
# Mac Rel Builder
#
B('Webkit Mac Builder', 'webkit_mac_rel', 'compile', 'webkit_mac_rel',
  builddir='webkit-mac-rel')
F('webkit_mac_rel', mac().ChromiumFactory(
    'webkit-mac-rel',
    slave_type='Builder',
    options=['--', '-project', '../webkit/webkit.xcodeproj']))

#
# Mac Rel Webkit testers
#
B('Webkit Mac10.5', 'webkit_rel_tests', 'testers', 'webkit_mac_rel_dep')
F('webkit_rel_tests', mac().ChromiumFactory(
    'webkit-mac-rel',
    slave_type='Tester',
    build_url=rel_archive,
    tests=['test_shell', 'webkit', 'webkit_unit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com'}))

################################################################################
## Debug
################################################################################

dbg_archive = master_config.GetArchiveUrl('Chromium',
                                          'Webkit Mac Builder (dbg)',
                                          'webkit-mac-dbg', 'mac')

#
# Main debug scheduler for src/
#
S('webkit_mac_dbg', branch='src', treeStableTimer=60)

#
# Dependent scheduler for the dbg builder
#
D('webkit_mac_dbg_dep', 'webkit_mac_dbg')

#
# Mac Dbg Builder
#
B('Webkit Mac Builder (dbg)', 'webkit_mac_dbg', 'compile', 'webkit_mac_dbg',
  builddir='webkit-mac-dbg')
F('webkit_mac_dbg', mac().ChromiumFactory(
    'webkit-mac-dbg',
    target='Debug',
    slave_type='Builder',
    options=['--', '-project', '../webkit/webkit.xcodeproj']))

#
# Mac Dbg Webkit  testers
#

B('Webkit Mac10.5 (dbg)(1)', 'webkit_dbg_tests_1', 'testers',
  'webkit_mac_rel_dep')
F('webkit_dbg_tests_1', mac().ChromiumFactory(
    'webkit-mac-dbg',
    slave_type='Tester',
    target='Debug',
    build_url=dbg_archive,
    tests=['webkit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '1:3'}))

B('Webkit Mac10.5 (dbg)(2)', 'webkit_dbg_tests_2', 'testers',
  'webkit_mac_rel_dep')
F('webkit_dbg_tests_2', mac().ChromiumFactory(
    'webkit-mac-dbg',
    slave_type='Tester',
    target='Debug',
    build_url=dbg_archive,
    tests=['webkit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '2:3'}))

B('Webkit Mac10.5 (dbg)(3)', 'webkit_dbg_tests_3', 'testers',
  'webkit_mac_rel_dep')
F('webkit_dbg_tests_3', mac().ChromiumFactory(
    'webkit-mac-dbg',
    slave_type='Tester',
    target='Debug',
    build_url=dbg_archive,
    tests=['test_shell', 'webkit', 'webkit_unit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '3:3'}))

def Update(config, active_master, c):
  return helper.Update(c)
