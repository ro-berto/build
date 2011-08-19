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
                                          'Webkit Mac Builder (CG)(deps)',
                                          'webkit-mac-pinned-cg-rel', 'mac')

#
# Main release scheduler for chromium
#
S('s2_chromium_rel', branch='src', treeStableTimer=60)

#
# Dependent scheduler for the dbg builder
#
D('s2_chromium_rel_dep', 's2_chromium_rel')

#
# Mac Rel Builder using Core Graphics
#
B('Webkit Mac Builder (CG)(deps)', 'f_webkit_mac_cg_rel',
  scheduler='s2_chromium_rel', builddir='webkit-mac-pinned-cg-rel')
F('f_webkit_mac_cg_rel', mac().ChromiumFactory(
    slave_type='Builder',
    options=[
        '--compiler=clang','--', '-project', '../webkit/webkit.xcodeproj'],
    factory_properties={
        'gclient_env': {
            'GYP_DEFINES':'clang=1 clang_use_chrome_plugins=1'
        },
    }))

#
# Mac Rel Webkit testers using Core Graphics
#
B('Webkit Mac10.6 (CG)(deps)', 'f_webkit_cg_rel_tests',
  scheduler='s2_chromium_rel_dep')
F('f_webkit_cg_rel_tests', mac().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=['test_shell', 'webkit', 'webkit_gpu', 'webkit_unit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com'}))

################################################################################
## Debug
################################################################################

dbg_archive = master_config.GetArchiveUrl('ChromiumWebkit',
                                          'Webkit Mac Builder (CG)(deps)(dbg)',
                                          'webkit-mac-pinned-cg-dbg', 'mac')

#
# Main debug scheduler for chromium
#
S('s2_chromium_dbg', branch='src', treeStableTimer=60)

#
# Dependent scheduler for the dbg builder
#
D('s2_chromium_dbg_dep', 's2_chromium_dbg')

#
# Mac Dbg Builder using Core Graphics
#
B('Webkit Mac Builder (CG)(deps)(dbg)', 'f_webkit_mac_cg_dbg',
  scheduler='s2_chromium_dbg', builddir='webkit-mac-pinned-cg-dbg')
F('f_webkit_mac_cg_dbg', mac().ChromiumFactory(
    target='Debug',
    slave_type='Builder',
    options=[
        '--compiler=clang','--', '-project', '../webkit/webkit.xcodeproj'],
    factory_properties={
        'gclient_env': {
            'GYP_DEFINES':'clang=1 clang_use_chrome_plugins=1'
        },
    }))

#
# Mac Dbg Webkit testers using Core Graphics
#

B('Webkit Mac10.6 (CG)(deps)(dbg)(1)', 'f_webkit_cg_dbg_tests_1',
  scheduler='s2_chromium_dbg_dep')
F('f_webkit_cg_dbg_tests_1', mac().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['test_shell', 'webkit', 'webkit_gpu', 'webkit_unit'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '1:2'}))

B('Webkit Mac10.6 (CG)(deps)(dbg)(2)', 'f_webkit_cg_dbg_tests_2',
  scheduler='s2_chromium_dbg_dep')
F('f_webkit_cg_dbg_tests_2', mac().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['webkit', 'webkit_gpu'],
    factory_properties={'archive_webkit_results': True,
                        'test_results_server': 'test-results.appspot.com',
                        'layout_part': '2:2'}))

def Update(config, active_master, c):
  return helper.Update(c)
