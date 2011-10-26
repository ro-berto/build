# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Webkit test builders using the Core Graphics library.
#
# Note that we use the builder vs tester role separation differently
# here than in our other buildbot configurations.
#
# In this configuration, the testers build the tests themselves rather than
# extracting them from the builder.  That's because these testers always
# fetch from webkit HEAD, and by the time the tester runs, webkit HEAD may
# point at a different revision than it did when the builder fetched webkit.
#
# Even though the testers don't extract the build package from the builder,
# the builder is still useful because it can cycle more quickly than the
# builder+tester can, and can alert us more quickly to build breakages.
#
# If you have questions about this, you can ask nsylvain.

from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler

def mac(): return chromium_factory.ChromiumFactory('src/build', 'darwin')

defaults['category'] = '5webkit mac latest'

################################################################################
## Release
################################################################################

#
# Main release scheduler for webkit
#
S('s5_webkit_cg_rel', branch='trunk', treeStableTimer=60)

#
# Mac Rel Builder
#
B('Webkit Mac Builder (CG)', 'f_webkit_mac_cg_rel',
  scheduler='s5_webkit_cg_rel', builddir='webkit-mac-cg-latest-rel')
F('f_webkit_mac_cg_rel', mac().ChromiumWebkitLatestFactory(
    slave_type='Builder',
    options=[
        '--compiler=clang','--', '-project', '../webkit/webkit.xcodeproj'],
    factory_properties={
        'gclient_env': {
            'GYP_DEFINES':'clang=1 clang_use_chrome_plugins=1 use_skia=0'
        },
        'layout_test_platform': 'chromium-cg-mac',
    }))

#
# Mac Rel Webkit builder+testers
#

# For now, we force clang off for 10.5.  See http://crbug.com/96724
B('Webkit Mac10.5 (CG)', 'f_webkit_cg_rel_tests',
  scheduler='s5_webkit_cg_rel')
F('f_webkit_cg_rel_tests', mac().ChromiumWebkitLatestFactory(
    options=['--', '-project', '../webkit/webkit.xcodeproj'],
    tests=['test_shell', 'webkit', 'webkit_gpu', 'webkit_unit'],
    factory_properties={
        'archive_webkit_results': True,
        'gclient_env': {'GYP_DEFINES':'clang=0 use_skia=0'},
        'layout_test_platform': 'chromium-cg-mac',
        'test_results_server': 'test-results.appspot.com',
    }))

B('Webkit Mac10.6 (CG)', 'f_webkit_cg_rel_tests_106',
  scheduler='s5_webkit_cg_rel')
F('f_webkit_cg_rel_tests_106', mac().ChromiumWebkitLatestFactory(
    options=[
        '--compiler=clang', '--', '-project', '../webkit/webkit.xcodeproj'],
    tests=['test_shell', 'webkit', 'webkit_gpu', 'webkit_unit'],
    factory_properties={
        'archive_webkit_results': True,
        'gclient_env': {
            'GYP_DEFINES':'clang=1 clang_use_chrome_plugins=1 use_skia=0',
        },
        'layout_test_platform': 'chromium-cg-mac',
        'test_results_server': 'test-results.appspot.com',
    }))

################################################################################
## Debug
################################################################################

#
# Main debug scheduler for webkit
#
S('s5_webkit_cg_dbg', branch='trunk', treeStableTimer=60)

#
# Mac Dbg Builder
#
B('Webkit Mac Builder (CG)(dbg)', 'f_webkit_mac_cg_dbg',
  scheduler='s5_webkit_cg_dbg', builddir='webkit-mac-cg-latest-dbg')
F('f_webkit_mac_cg_dbg', mac().ChromiumWebkitLatestFactory(
    target='Debug',
    slave_type='Builder',
    options=[
        '--compiler=clang','--', '-project', '../webkit/webkit.xcodeproj'],
    factory_properties={
        'gclient_env': {
            'GYP_DEFINES':'clang=1 clang_use_chrome_plugins=1 use_skia=0'
        },
        'layout_test_platform': 'chromium-cg-mac',
    }))

#
# Mac Dbg Webkit builder+testers
#

# For now, we force clang off for 10.5.  See http://crbug.com/96724
B('Webkit Mac10.5 (CG)(dbg)(1)', 'f_webkit_cg_dbg_tests_1',
  scheduler='s5_webkit_cg_dbg')
F('f_webkit_cg_dbg_tests_1', mac().ChromiumWebkitLatestFactory(
    target='Debug',
    options=['--', '-project', '../webkit/webkit.xcodeproj'],
    tests=['test_shell', 'webkit', 'webkit_gpu', 'webkit_unit'],
    factory_properties={
        'archive_webkit_results': True,
        'gclient_env': {'GYP_DEFINES':'clang=0 use_skia=0'},
        'layout_part': '1:2',
        'layout_test_platform': 'chromium-cg-mac',
        'test_results_server': 'test-results.appspot.com',
    }))

# For now, we force clang off for 10.5.  See http://crbug.com/96724
B('Webkit Mac10.5 (CG)(dbg)(2)', 'f_webkit_cg_dbg_tests_2',
  scheduler='s5_webkit_cg_dbg')
F('f_webkit_cg_dbg_tests_2', mac().ChromiumWebkitLatestFactory(
    target='Debug',
    options=['--', '-project', '../webkit/webkit.xcodeproj'],
    tests=['webkit', 'webkit_gpu'],
    factory_properties={
        'archive_webkit_results': True,
        'gclient_env': {'GYP_DEFINES':'clang=0 use_skia=0'},
        'layout_part': '2:2',
        'layout_test_platform': 'chromium-cg-mac',
        'test_results_server': 'test-results.appspot.com',
    }))

B('Webkit Mac10.6 (CG)(dbg)', 'f_webkit_cg_dbg_tests',
  scheduler='s5_webkit_cg_dbg')
F('f_webkit_cg_dbg_tests', mac().ChromiumWebkitLatestFactory(
    target='Debug',
    options=[
        '--compiler=clang', '--', '-project', '../webkit/webkit.xcodeproj'],
    tests=['test_shell', 'webkit', 'webkit_gpu', 'webkit_unit'],
    factory_properties={
        'archive_webkit_results': True,
        'gclient_env': {
            'GYP_DEFINES':'clang=1 clang_use_chrome_plugins=1 use_skia=0',
        },
        'layout_test_platform': 'chromium-cg-mac',
        'test_results_server': 'test-results.appspot.com',
    }))

################################################################################
##
################################################################################

def Update(config, active_master, c):
  return helper.Update(c)
