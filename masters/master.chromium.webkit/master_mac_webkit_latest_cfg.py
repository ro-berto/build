# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler

def mac(): return chromium_factory.ChromiumFactory('src/build', 'darwin')


################################################################################
## Release
################################################################################

defaults['category'] = '5webkit mac latest'

#
# Main release schedulers for chromium and webkit
#
S('s5_chromium_rel', branch='src', treeStableTimer=60)
S('s5_webkit_rel', branch='trunk', treeStableTimer=60)

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
  scheduler='s5_chromium_rel|s5_webkit_rel')
F('f_webkit_rel_tests', mac().ChromiumWebkitLatestFactory(
    options=['--', '-project', '../webkit/webkit.xcodeproj'],
    tests=['test_shell', 'webkit', 'webkit_gpu', 'webkit_unit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com'}))

################################################################################
## Debug
################################################################################

#
# Main debug schedulers for chromium and webkit
#
S('s5_chromium_dbg', branch='src', treeStableTimer=60)
S('s5_webkit_dbg', branch='trunk', treeStableTimer=60)

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
  scheduler='s5_chromium_dbg|s5_webkit_dbg')
F('f_webkit_dbg_tests_1', mac().ChromiumWebkitLatestFactory(
    target='Debug',
    options=['--', '-project', '../webkit/webkit.xcodeproj'],
    tests=['test_shell', 'webkit', 'webkit_gpu', 'webkit_unit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '1:2'}))

B('Webkit Mac10.5 (dbg)(2)', 'f_webkit_dbg_tests_2',
  scheduler='s5_chromium_dbg|s5_webkit_dbg')
F('f_webkit_dbg_tests_2', mac().ChromiumWebkitLatestFactory(
    target='Debug',
    options=['--', '-project', '../webkit/webkit.xcodeproj'],
    tests=['webkit', 'webkit_gpu'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '2:2'}))

def Update(config, active_master, c):
  return helper.Update(c)
