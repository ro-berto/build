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

defaults['category'] = '5webkit mac latest'

# Archive location
rel_archive = master_config.GetArchiveUrl('ChromiumWebkit',
                                          'Webkit Mac Builder',
                                          'webkit-mac-latest-rel', 'mac')

#
# Main release schedulers for chromium and webkit
#
S('s5_chromium_rel', branch='src', treeStableTimer=60)
S('s5_webkit_rel', branch='trunk', treeStableTimer=60)

#
# Dependent schedulers for the release builder
#
D('s5_chromium_rel_dep', 's5_chromium_rel')
D('s5_webkit_rel_dep', 's5_webkit_rel')

#
# Mac Rel Builder
#
B('Webkit Mac Builder', 'f_webkit_mac_rel',
  scheduler='s5_chromium_rel|s5_webkit_rel', builddir='webkit-mac-latest-rel')
F('f_webkit_mac_rel', mac().ChromiumWebkitLatestFactory(
    slave_type='Builder',
    options=['--', '-project', '../webkit/webkit.xcodeproj']))

#
# Mac Rel Webkit testers
#
B('Webkit Mac10.5', 'f_webkit_rel_tests',
  scheduler='s5_chromium_rel_dep|s5_webkit_rel_dep')
F('f_webkit_rel_tests', mac().ChromiumWebkitLatestFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=['test_shell', 'webkit', 'webkit_gpu', 'webkit_unit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com'}))

################################################################################
## Debug
################################################################################

dbg_archive = master_config.GetArchiveUrl('ChromiumWebkit',
                                          'Webkit Mac Builder (dbg)',
                                          'webkit-mac-latest-dbg', 'mac')

#
# Main debug schedulers for chromium and webkit
#
S('s5_chromium_dbg', branch='src', treeStableTimer=60)
S('s5_webkit_dbg', branch='trunk', treeStableTimer=60)

#
# Dependent schedulers for the dbg builder
#
D('s5_chromium_dbg_dep', 's5_chromium_dbg')
D('s5_webkit_dbg_dep', 's5_webkit_dbg')

#
# Mac Dbg Builder
#
B('Webkit Mac Builder (dbg)', 'f_webkit_mac_dbg',
  scheduler='s5_chromium_dbg|s5_webkit_dbg', builddir='webkit-mac-latest-dbg')
F('f_webkit_mac_dbg', mac().ChromiumWebkitLatestFactory(
    target='Debug',
    slave_type='Builder',
    options=['--', '-project', '../webkit/webkit.xcodeproj']))

#
# Mac Dbg Webkit testers
#

B('Webkit Mac10.5 (dbg)(1)', 'f_webkit_dbg_tests_1',
  scheduler='s5_chromium_dbg_dep|s5_webkit_dbg_dep')
F('f_webkit_dbg_tests_1', mac().ChromiumWebkitLatestFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['test_shell', 'webkit', 'webkit_gpu', 'webkit_unit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '1:2'}))

B('Webkit Mac10.5 (dbg)(2)', 'f_webkit_dbg_tests_2',
  scheduler='s5_chromium_dbg_dep|s5_webkit_dbg_dep')
F('f_webkit_dbg_tests_2', mac().ChromiumWebkitLatestFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['webkit', 'webkit_gpu'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '2:2'}))

def Update(config, active_master, c):
  return helper.Update(c)
