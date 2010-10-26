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

def linux(): return chromium_factory.ChromiumFactory('src/build', 'linux2')


################################################################################
## Release
################################################################################

defaults['category'] = '4linux'

# Archive location
rel_archive_x64 = master_config.GetArchiveUrl('Chromium', 'Linux Builder x64',
                                              'cr-linux-rel-x64', 'linux')

#
# Main debug scheduler for src/
#
S('linux_rel', branch='src', treeStableTimer=60)

#
# Dependent scheduler for the dbg builder
#
D('linux_rel_dep', 'linux_rel')

#
# Linux Rel Builder
#
B('Linux Builder x64', 'rel', 'compile', 'linux_rel', builddir='cr-linux-rel-x64')
F('rel', linux().ChromiumFactory(
    'chromium-linux-rel-64',
    slave_type='Builder',
    options=['app_unittests', 'browser_tests', 'googleurl_unittests',
             'gpu_unittests', 'ipc_tests', 'media_unittests', 'memory_test',
             'page_cycler_tests', 'printing_unittests', 'remoting_unittests',
             'startup_tests', 'sync_unit_tests', 'ui_tests', 'unit_tests',
             'url_fetch_test', 'base_unittests', 'net_unittests']))

#
# Linux Rel testers
#
B('Linux Tests x64', 'rel_unit', 'testers', 'linux_rel_dep')
F('rel_unit', linux().ChromiumFactory(
    'chromium-linux-rel-64',
    slave_type='Tester',
    build_url=rel_archive_x64,
    tests=['check_deps', 'googleurl', 'media', 'printing', 'remoting', 'ui',
           'browser_tests', 'unit', 'gpu', 'base', 'net']))



################################################################################
## Debug
################################################################################

dbg_archive = master_config.GetArchiveUrl('Chromium', 'Linux Builder (dbg)',
                                          'cr-linux-dbg', 'linux')

dbg_shlib_archive = master_config.GetArchiveUrl('Chromium',
                                                'Linux Builder (dbg-shlib)',
                                                'cr-linux-dbg-shlib',
                                                'linux')

#
# Main debug scheduler for src/
#
S('linux_dbg', branch='src', treeStableTimer=60)
S('linux_dbg_shlib', branch='src', treeStableTimer=60)

#
# Dependent scheduler for the dbg builder
#
D('linux_dbg_dep', 'linux_dbg')
D('linux_dbg_shlib_dep', 'linux_dbg_shlib')

#
# Linux Dbg Builder
#
B('Linux Builder (dbg)', 'dbg', 'compile', 'linux_dbg', builddir='cr-linux-dbg')
F('dbg', linux().ChromiumFactory(
    'chromium-linux-dbg',
    slave_type='Builder',
    target='Debug',
    options=['app_unittests', 'browser_tests', 'googleurl_unittests',
             'gpu_unittests', 'interactive_ui_tests', 'ipc_tests',
             'media_unittests', 'nacl_ui_tests', 'printing_unittests',
             'remoting_unittests', 'sync_unit_tests', 'ui_tests', 'unit_tests',
             'nacl_sandbox_tests', 'base_unittests', 'net_unittests']))

#
# Linux Dbg Unit testers
#

B('Linux Tests (dbg)(1)', 'dbg_unit_1', 'testers', 'linux_dbg_dep')
F('dbg_unit_1', linux().ChromiumFactory(
    'chromium-linux-dbg',
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['check_deps', 'googleurl', 'media', 'printing', 'remoting', 'ui',
           'browser_tests', 'base'],
    factory_properties={'ui_total_shards': 2,
                        'ui_shard_index': 1,
                        'generate_gtest_json': True}))

B('Linux Tests (dbg)(2)', 'dbg_unit_2', 'testers', 'linux_dbg_dep')
F('dbg_unit_2', linux().ChromiumFactory(
    'chromium-linux-dbg',
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['unit', 'ui', 'nacl_ui', 'gpu', 'interactive_ui', 'nacl_sandbox',
           'net', 'plugin',],
    factory_properties={'ui_total_shards': 2,
                        'ui_shard_index': 2,
                        'generate_gtest_json': True}))

#
# Linux Dbg Shared Builder
#
B('Linux Builder (dbg-shlib)', 'dbg_shlib', 'compile', 'linux_dbg_shlib',
   builddir='cr-linux-dbg-shlib')
F('dbg_shlib', linux().ChromiumFactory(
    'chromium-linux-dbg-shlib',
    slave_type='Builder',
    target='Debug',
    options=['--build-tool=make'],
    factory_properties={
        'gclient_env': {'GYP_DEFINES':'library=shared_library'}}))

#
# Linux Dbg Shared Unit testers
#

B('Linux Tests (dbg-shlib)', 'dbg_shlib_unit', 'testers', 'linux_dbg_shlib_dep')
F('dbg_shlib_unit', linux().ChromiumFactory(
    'chromium-linux-dbg-shlib',
    target='Debug',
    slave_type='Tester',
    build_url=dbg_shlib_archive,
    tests=['base', 'browser_tests', 'check_deps', 'googleurl', 'media', 'net',
           'printing', 'remoting', 'sizes', 'test_shell', 'ui', 'unit']))


def Update(config, active_master, c):
  return helper.Update(c)
