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

defaults['category'] = '2webkit mac deps'

# Archive location
rel_archive = master_config.GetArchiveUrl('ChromiumWebkit',
                                          'Webkit Mac Builder (deps)',
                                          'webkit-mac-pinned-rel', 'mac')

#
# Main release scheduler for chromium
#
S('s2_chromium_rel', branch='src', treeStableTimer=60)

#
# Dependent scheduler for the dbg builder
#
D('s2_chromium_rel_dep', 's2_chromium_rel')

#
# Mac Rel Builder
#
B('Webkit Mac Builder (deps)', 'f_webkit_mac_rel',
  scheduler='s2_chromium_rel', builddir='webkit-mac-pinned-rel')
F('f_webkit_mac_rel', mac().ChromiumFactory(
    slave_type='Builder',
    options=['--', '-project', '../webkit/webkit.xcodeproj']))

#
# Mac Rel Webkit testers
#
B('Webkit Mac10.5 (deps)', 'f_webkit_rel_tests',
  scheduler='s2_chromium_rel_dep')
F('f_webkit_rel_tests', mac().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=['test_shell', 'webkit', 'webkit_unit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com'}))

################################################################################
## Debug
################################################################################

dbg_archive = master_config.GetArchiveUrl('ChromiumWebkit',
                                          'Webkit Mac Builder (deps)(dbg)',
                                          'webkit-mac-pinned-dbg', 'mac')

#
# Main debug scheduler for chromium
#
S('s2_chromium_dbg', branch='src', treeStableTimer=60)

#
# Dependent scheduler for the dbg builder
#
D('s2_chromium_dbg_dep', 's2_chromium_dbg')

#
# Mac Dbg Builder
#
B('Webkit Mac Builder (deps)(dbg)', 'f_webkit_mac_dbg',
  scheduler='s2_chromium_dbg', builddir='webkit-mac-pinned-dbg')
F('f_webkit_mac_dbg', mac().ChromiumFactory(
    target='Debug',
    slave_type='Builder',
    options=['--', '-project', '../webkit/webkit.xcodeproj']))

#
# Mac Dbg Webkit testers
#

B('Webkit Mac10.5 (deps)(dbg)(1)', 'f_webkit_dbg_tests_1',
  scheduler='s2_chromium_dbg_dep')
F('f_webkit_dbg_tests_1', mac().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['test_shell', 'webkit', 'webkit_unit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '1:2'}))

B('Webkit Mac10.5 (deps)(dbg)(2)', 'f_webkit_dbg_tests_2',
  scheduler='s2_chromium_dbg_dep')
F('f_webkit_dbg_tests_2', mac().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['webkit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '2:2'}))

def Update(config, active_master, c):
  return helper.Update(c)
