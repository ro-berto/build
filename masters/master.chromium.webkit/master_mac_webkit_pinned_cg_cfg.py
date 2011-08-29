# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Webkit test builders using the Core Graphics library.

from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
D = helper.Dependent
F = helper.Factory
S = helper.Scheduler

def mac(): return chromium_factory.ChromiumFactory('src/build', 'darwin')

defaults['category'] = '2webkit mac deps'

################################################################################
## Release
################################################################################

# Archive location
cg_rel_builddir = 'webkit-mac-pinned-cg-rel'
cg_rel_archive = master_config.GetArchiveUrl(
    'ChromiumWebkit', 'Webkit Mac Builder (CG)(deps)',
    cg_rel_builddir, 'mac')

#
# Main release scheduler for chromium
#
cg_rel_scheduler = 's2_chromium_cg_rel'
S(cg_rel_scheduler, branch='src', treeStableTimer=60)

#
# Dependent scheduler for the dbg builder
#
cg_rel_dep_scheduler = 's2_chromium_cg_rel_dep'
D(cg_rel_dep_scheduler, cg_rel_scheduler)

#
# Mac Rel Builder
#
B('Webkit Mac Builder (CG)(deps)', 'f_webkit_mac_cg_rel',
  scheduler=cg_rel_scheduler, builddir=cg_rel_builddir)
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
# Mac Rel Webkit testers
#
B('Webkit Mac10.6 (CG)(deps)', 'f_webkit_cg_rel_tests',
  scheduler=cg_rel_dep_scheduler)
F('f_webkit_cg_rel_tests', mac().ChromiumFactory(
    slave_type='Tester',
    build_url=cg_rel_archive,
    tests=['test_shell', 'webkit', 'webkit_gpu', 'webkit_unit'],
    factory_properties={
        'archive_webkit_results': True,
        'test_results_server': 'test-results.appspot.com',
    }))

################################################################################
## Debug
################################################################################

cg_dbg_builddir = 'webkit-mac-pinned-cg-dbg'
cg_dbg_archive = master_config.GetArchiveUrl(
    'ChromiumWebkit', 'Webkit Mac Builder (CG)(deps)(dbg)',
    cg_dbg_builddir, 'mac')

#
# Main debug scheduler for chromium
#
cg_dbg_scheduler = 's2_chromium_cg_dbg'
S(cg_dbg_scheduler, branch='src', treeStableTimer=60)

#
# Dependent scheduler for the dbg builder
#
cg_dbg_dep_scheduler = 's2_chromium_cg_dbg_dep'
D(cg_dbg_dep_scheduler, cg_dbg_scheduler)

#
# Mac Dbg Builder
#
B('Webkit Mac Builder (CG)(deps)(dbg)', 'f_webkit_mac_cg_dbg',
  scheduler=cg_dbg_scheduler, builddir=cg_dbg_builddir)
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
# Mac Dbg Webkit testers
#

B('Webkit Mac10.6 (CG)(deps)(dbg)(1)', 'f_webkit_cg_dbg_tests_1',
  scheduler=cg_dbg_dep_scheduler)
F('f_webkit_cg_dbg_tests_1', mac().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=cg_dbg_archive,
    tests=['test_shell', 'webkit', 'webkit_gpu', 'webkit_unit'],
    factory_properties={
        'archive_webkit_results': True,
        'layout_part': '1:2',
        'test_results_server': 'test-results.appspot.com',
    }))

B('Webkit Mac10.6 (CG)(deps)(dbg)(2)', 'f_webkit_cg_dbg_tests_2',
  scheduler=cg_dbg_dep_scheduler)
F('f_webkit_cg_dbg_tests_2', mac().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=cg_dbg_archive,
    tests=['webkit', 'webkit_gpu'],
    factory_properties={
        'archive_webkit_results': True,
        'layout_part': '2:2',
        'test_results_server': 'test-results.appspot.com',
    }))

################################################################################
##
################################################################################

def Update(config, active_master, c):
  return helper.Update(c)
