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
            'GYP_DEFINES':'clang=1 clang_use_chrome_plugins=1 use_skia=0'
        },
        'layout_test_platform': 'chromium-cg-mac',
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
        'layout_test_platform': 'chromium-cg-mac',
        'test_results_server': 'test-results.appspot.com',
    }))

################################################################################
##
################################################################################

def Update(config, active_master, c):
  return helper.Update(c)
