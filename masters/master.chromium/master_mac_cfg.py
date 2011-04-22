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

def mac(): return chromium_factory.ChromiumFactory('src/build', 'darwin')


################################################################################
## Release
################################################################################

defaults['category'] = '3mac'

# Archive location
rel_archive = master_config.GetArchiveUrl('Chromium', 'Mac Builder',
                                          'cr-mac-rel', 'mac')

#
# Main debug scheduler for src/
#
S('mac_rel', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the dbg builder
#
T('mac_rel_trigger')

#
# Mac Rel Builder
#
B('Mac Builder', 'rel', 'compile', 'mac_rel', builddir='cr-mac-rel')
F('rel', mac().ChromiumFactory(
    slave_type='Builder',
    options=['--', '-target', 'chromium_builder_tests'],
    factory_properties={'trigger': 'mac_rel_trigger'}))

#
# Mac Rel testers
#
B('Mac10.5 Tests (1)', 'rel_unit_1', 'testers', 'mac_rel_trigger')
F('rel_unit_1', mac().ChromiumFactory(
  slave_type='Tester',
  build_url=rel_archive,
  tests=['ui', 'media', 'printing', 'remoting', 'gpu', 'googleurl',
         'nacl_ui', 'nacl_integration', 'nacl_sandbox',
         'base', 'net', 'safe_browsing', 'crypto'],
  factory_properties={'generate_gtest_json': True})
)

B('Mac10.5 Tests (2)', 'rel_unit_2', 'testers', 'mac_rel_trigger')
F('rel_unit_2', mac().ChromiumFactory(
  slave_type='Tester',
  build_url=rel_archive,
  tests=['unit', 'browser_tests'],
  factory_properties={'generate_gtest_json': True})
)

B('Mac10.6 Tests (1)', 'rel_unit_1', 'testers', 'mac_rel_trigger')
B('Mac10.6 Tests (2)', 'rel_unit_2', 'testers', 'mac_rel_trigger')

B('Mac10.6 Sync', 'rel_sync', 'testers', 'mac_rel_trigger')
F('rel_sync', mac().ChromiumFactory(
  slave_type='Tester',
  build_url=rel_archive,
  tests=['sync_integration'],
  factory_properties={'generate_gtest_json': True}))

################################################################################
## Debug
################################################################################

dbg_archive = master_config.GetArchiveUrl('Chromium', 'Mac Builder (dbg)',
                                          'cr-mac-dbg', 'mac')

#
# Main debug scheduler for src/
#
S('mac_dbg', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the dbg builder
#
T('mac_dbg_trigger')

#
# Mac Dbg Builder
#
B('Mac Builder (dbg)', 'dbg', 'compile', 'mac_dbg', builddir='cr-mac-dbg')
F('dbg', mac().ChromiumFactory(
    target='Debug',
    slave_type='Builder',
    options=['--', '-target', 'chromium_builder_tests'],
    factory_properties={'trigger': 'mac_dbg_trigger'}))

#
# Mac Dbg Unit testers
#

B('Mac 10.5 Tests (dbg)(1)', 'dbg_unit_1', 'testers', 'mac_dbg_trigger')
F('dbg_unit_1', mac().ChromiumFactory(
  slave_type='Tester',
  target='Debug',
  build_url=dbg_archive,
  tests=['check_deps', 'media', 'printing', 'remoting', 'unit', 'googleurl',
         'nacl_ui', 'nacl_integration', 'nacl_sandbox', 'gpu', 'interactive_ui',
         'base', 'crypto', 'safe_browsing'],
  factory_properties={'generate_gtest_json': True}))

B('Mac 10.5 Tests (dbg)(2)', 'dbg_unit_2', 'testers', 'mac_dbg_trigger')
F('dbg_unit_2', mac().ChromiumFactory(
  slave_type='Tester',
  target='Debug',
  build_url=dbg_archive,
  tests=['ui', 'net'],
  factory_properties={'generate_gtest_json': True}))

B('Mac 10.5 Tests (dbg)(3)', 'dbg_unit_3', 'testers', 'mac_dbg_trigger')
F('dbg_unit_3', mac().ChromiumFactory(
  slave_type='Tester',
  target='Debug',
  build_url=dbg_archive,
  tests=['browser_tests'],
  factory_properties={'generate_gtest_json': True}))

B('Mac 10.6 Tests (dbg)(1)', 'dbg_unit_1', 'testers', 'mac_dbg_trigger')
B('Mac 10.6 Tests (dbg)(2)', 'dbg_unit_2', 'testers', 'mac_dbg_trigger')
B('Mac 10.6 Tests (dbg)(3)', 'dbg_unit_3', 'testers', 'mac_dbg_trigger')

#
# Mac Dbg Clang bot
#

B('Mac Clang (dbg)', 'dbg_mac_clang', 'compile', 'mac_dbg')
F('dbg_mac_clang', mac().ChromiumFactory(
    target='Debug',
    options=['--compiler=clang'],
    # Only include test binaries that run reasonably fast and that don't contain
    # many flaky tests.
    tests=[
        'base', 'gfx', 'crypto',
        # Adds ipc_tests, sync_unit_tests, unit_tests, and app_unittests
        # unit_tests is very flaky due to http://crbug.com/60426
        # TODO(thakis): Re-add this once the bug is fixed.
        #'unit',
    ],
    factory_properties={
        'gclient_env': {
            'GYP_DEFINES':'clang=1 clang_use_chrome_plugins=1'
    }}))


def Update(config, active_master, c):
  return helper.Update(c)
