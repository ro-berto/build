# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler
T = helper.Triggerable

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
# Triggerable scheduler for the rel builder
#
T('linux_rel_trigger')

#
# Linux Rel Builder
#
B('Linux Builder x64', 'rel', 'compile', 'linux_rel',
  builddir='cr-linux-rel-x64')
F('rel', linux().ChromiumFactory(
    slave_type='Builder',
    options=['app_unittests', 'browser_tests', 'googleurl_unittests',
             'gpu_unittests', 'ipc_tests', 'media_unittests', 'memory_test',
             'page_cycler_tests', 'printing_unittests', 'remoting_unittests',
             'startup_tests', 'sync_unit_tests', 'ui_tests', 'unit_tests',
             'url_fetch_test', 'base_unittests', 'net_unittests',
             'gfx_unittests', 'safe_browsing_tests', 'sync_integration_tests'],
    factory_properties={'trigger': 'linux_rel_trigger'}))

#
# Linux Rel testers
#
B('Linux Tests x64', 'rel_unit', 'testers', 'linux_rel_trigger')
F('rel_unit', linux().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive_x64,
    tests=['check_deps', 'googleurl', 'media', 'printing', 'remoting', 'ui',
           'browser_tests', 'unit', 'gpu', 'base', 'net', 'safe_browsing'],
    factory_properties={'generate_gtest_json': True}))

B('Linux Sync', 'rel_sync', 'testers', 'linux_rel_trigger')
F('rel_sync', linux().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive_x64,
    tests=['sync_integration']))


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

#
# Triggerable scheduler for the dbg shlib builder
#
T('linux_dbg_shlib_trigger')

#
# Linux Dbg Builder
#
B('Linux Builder (dbg)', 'dbg', 'compile', 'linux_dbg', builddir='cr-linux-dbg')
F('dbg', linux().ChromiumFactory(
    slave_type='Builder',
    target='Debug',
    options=['app_unittests', 'browser_tests', 'googleurl_unittests',
             'gpu_unittests', 'interactive_ui_tests', 'ipc_tests',
             'media_unittests', 'nacl_ui_tests', 'printing_unittests',
             'remoting_unittests', 'sync_unit_tests', 'ui_tests', 'unit_tests',
             'nacl_sandbox_tests', 'base_unittests', 'net_unittests',
             'gfx_unittests', 'plugin_tests', 'safe_browsing_tests']))

#
# Linux Dbg Unit testers
#

B('Linux Tests (dbg)(1)', 'dbg_unit_1', 'testers', 'linux_dbg')
F('dbg_unit_1', linux().ChromiumFactory(
    target='Debug',
    tests=['check_deps', 'ui', 'browser_tests'],
    options=['browser_tests',  'ui_tests'],
    factory_properties={'generate_gtest_json': True}))

B('Linux Tests (dbg)(2)', 'dbg_unit_2', 'testers', 'linux_dbg')
F('dbg_unit_2', linux().ChromiumFactory(
    target='Debug',
    tests=['unit', 'nacl_ui', 'gpu', 'interactive_ui', 'nacl_sandbox',
           'net', 'plugin', 'googleurl', 'media', 'printing', 'remoting',
           'base', 'safe_browsing'],
    options=['app_unittests', 'googleurl_unittests', 'gpu_unittests',
             'interactive_ui_tests', 'ipc_tests', 'media_unittests',
             'nacl_ui_tests', 'printing_unittests', 'remoting_unittests',
             'sync_unit_tests', 'unit_tests', 'nacl_sandbox_tests',
             'base_unittests', 'net_unittests', 'plugin_tests',
             'safe_browsing_tests', 'gfx_unittests'],
    factory_properties={'generate_gtest_json': True}))

#
# Linux Dbg Shared Builder
#
B('Linux Builder (dbg-shlib)', 'dbg_shlib', 'compile', 'linux_dbg',
   builddir='cr-linux-dbg-shlib')
F('dbg_shlib', linux().ChromiumFactory(
    slave_type='Builder',
    target='Debug',
    options=['--build-tool=make'],
    factory_properties={
        'gclient_env': {'GYP_DEFINES':'library=shared_library'},
        'trigger': 'linux_dbg_shlib_trigger'}))

#
# Linux Dbg Shared Unit testers
#

B('Linux Tests (dbg-shlib)', 'dbg_shlib_unit', 'testers',
  'linux_dbg_shlib_trigger')
F('dbg_shlib_unit', linux().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_shlib_archive,
    tests=['base', 'browser_tests', 'check_deps', 'googleurl', 'media', 'net',
           'printing', 'remoting', 'sizes', 'test_shell', 'ui', 'unit'],
    factory_properties={'generate_gtest_json': True}))

#
# Linux Dbg Clang bots
#

B('Linux Clang (dbg)', 'dbg_linux_clang', 'compile', 'linux_dbg')
F('dbg_linux_clang', linux().ChromiumFactory(
    target='Debug',
    options=['--build-tool=make', '--compiler=clang'],
    tests=['base', 'gfx', 'unit'],
    factory_properties={
        'gclient_env': {
            'GYP_DEFINES':'clang=1 clang_use_chrome_plugins=1 fastbuild=1'
    }}))

#
# Linux Views Dbg Clang bot
#

B('Linux Views Clang (dbg)', 'dbg_linux_views_clang', 'compile', 'linux_dbg')
F('dbg_linux_views_clang', linux().ChromiumFactory(
    target='Debug',
    options=['--build-tool=make', '--compiler=clang'],
    tests=['base', 'ui_base', 'gfx', 'unit'],
    factory_properties={
        'gclient_env': {
            'GYP_DEFINES':'clang=1 clang_use_chrome_plugins=1 ' + 
                          'toolkit_views=1 fastbuild=1'
    }}))


def Update(config, active_master, c):
  return helper.Update(c)
