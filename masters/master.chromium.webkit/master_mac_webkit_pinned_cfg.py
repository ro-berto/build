# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Webkit test builders using the Skia graphics library.

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

# Temporarily define these in a single place for easier local override of
# build options.
# As noted in http://crbug.com/97423 , this should be reverted by 31 Oct 2011.
builder_options = [
    '--compiler=clang', '--', '-project', '../webkit/webkit.xcodeproj']
gyp_defines = 'clang=1 clang_use_chrome_plugins=1 use_skia=1'

################################################################################
## Release
################################################################################

# Archive location
rel_builddir = 'webkit-mac-pinned-rel'
rel_archive = master_config.GetArchiveUrl(
    'ChromiumWebkit', 'Webkit Mac Builder (deps)',
    rel_builddir, 'mac')

#
# Main release scheduler for chromium
#
rel_scheduler = 's2_chromium_rel'
S(rel_scheduler, branch='src', treeStableTimer=60)

#
# Dependent scheduler for the dbg builder
#
rel_dep_scheduler = 's2_chromium_rel_dep'
D(rel_dep_scheduler, rel_scheduler)

#
# Mac Rel Builder
#
B('Webkit Mac Builder (deps)', 'f_webkit_mac_rel',
  scheduler=rel_scheduler, builddir=rel_builddir)
F('f_webkit_mac_rel', mac().ChromiumFactory(
    slave_type='Builder',
    options=builder_options,
    factory_properties={
        'gclient_env': {
            'GYP_DEFINES':gyp_defines,
        },
        'layout_test_platform': 'chromium-mac',
    }))

#
# Mac Rel Webkit testers
#
B('Webkit Mac10.6 (deps)', 'f_webkit_rel_tests',
  scheduler=rel_dep_scheduler)
F('f_webkit_rel_tests', mac().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=['test_shell', 'webkit', 'webkit_gpu', 'webkit_unit'],
    factory_properties={
        'archive_webkit_results': True,
        'layout_test_platform': 'chromium-mac',
        'test_results_server': 'test-results.appspot.com',
    }))

################################################################################
## Debug
################################################################################

dbg_builddir = 'webkit-mac-pinned-dbg'
dbg_archive = master_config.GetArchiveUrl(
    'ChromiumWebkit', 'Webkit Mac Builder (deps)(dbg)',
    dbg_builddir, 'mac')

#
# Main debug scheduler for chromium
#
dbg_scheduler = 's2_chromium_dbg'
S(dbg_scheduler, branch='src', treeStableTimer=60)

#
# Dependent scheduler for the dbg builder
#
dbg_dep_scheduler = 's2_chromium_dbg_dep'
D(dbg_dep_scheduler, dbg_scheduler)

#
# Mac Dbg Builder
#
B('Webkit Mac Builder (deps)(dbg)', 'f_webkit_mac_dbg',
  scheduler=dbg_scheduler, builddir=dbg_builddir)
F('f_webkit_mac_dbg', mac().ChromiumFactory(
    target='Debug',
    slave_type='Builder',
    options=builder_options,
    factory_properties={
        'gclient_env': {
            'GYP_DEFINES':gyp_defines,
        },
        'layout_test_platform': 'chromium-mac',
    }))

#
# Mac Dbg Webkit testers
#

B('Webkit Mac10.6 (deps)(dbg)(1)', 'f_webkit_dbg_tests_1',
  scheduler=dbg_dep_scheduler)
F('f_webkit_dbg_tests_1', mac().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['test_shell', 'webkit', 'webkit_gpu', 'webkit_unit'],
    factory_properties={
        'archive_webkit_results': True,
        'layout_part': '1:2',
        'layout_test_platform': 'chromium-mac',
        'test_results_server': 'test-results.appspot.com',
    }))

B('Webkit Mac10.6 (deps)(dbg)(2)', 'f_webkit_dbg_tests_2',
  scheduler=dbg_dep_scheduler)
F('f_webkit_dbg_tests_2', mac().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['webkit', 'webkit_gpu'],
    factory_properties={
        'archive_webkit_results': True,
        'layout_part': '2:2',
        'layout_test_platform': 'chromium-mac',
        'test_results_server': 'test-results.appspot.com',
    }))

################################################################################
##
################################################################################

def Update(config, active_master, c):
  return helper.Update(c)
