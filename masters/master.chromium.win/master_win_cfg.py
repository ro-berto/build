# Copyright (c) 2012 The Chromium Authors. All rights reserved.
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

def win():
  return chromium_factory.ChromiumFactory('src/build', 'win32')
def win_tester():
  return chromium_factory.ChromiumFactory(
      'src/build', 'win32', nohooks_on_update=True)

# Tests that are single-machine shard-safe. For now we only use the sharding
# supervisor for long tests (more than 30 seconds) that are known to be stable.
sharded_tests = [
  'base_unittests',
  'browser_tests',
  'media_unittests',
]

################################################################################
## Release
################################################################################

defaults['category'] = '2windows'

# Archive location
rel_archive = ''
# rel_archive = master_config.GetArchiveUrl('Chromium', 'Win Builder',
#                                           'cr-win-rel', 'win32')

#
# Main debug scheduler for src/
#
S('win_rel', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the rel builder
#
T('win_rel_trigger')

#
# Win Rel Builder
#
# B('Win Builder', 'rel', 'compile|windows', 'win_rel', builddir='cr-win-rel',
#   notify_on_missing=True)
F('rel', win().ChromiumFactory(
    slave_type='Builder',
    project='all.sln;chromium_builder_tests',
    factory_properties={'trigger': 'win_rel_trigger',
                        'gclient_env': {'GYP_DEFINES': 'fastbuild=1'}}))

#
# Win Rel testers
#
# B('XP Tests (1)', 'rel_unit_1', 'testers|windows', 'win_rel_trigger',
#   auto_reboot=True, notify_on_missing=True)
F('rel_unit_1', win_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=[
      'browser_tests',
      'cacheinvalidation',
      'courgette',
      'crypto',
      'googleurl',
      'gpu',
      'installer',
      'jingle',
      'media',
      'printing',
      'remoting',
      'safe_browsing',
      'sandbox',
    ],
    factory_properties={'process_dumps': True,
                        'sharded_tests': sharded_tests,
                        'browser_total_shards': 3, 'browser_shard_index': 1,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

# B('XP Tests (2)', 'rel_unit_2', 'testers|windows', 'win_rel_trigger',
#   auto_reboot=True, notify_on_missing=True)
F('rel_unit_2', win_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=[
      'base',
      'browser_tests',
      'net',
    ],
    factory_properties={'process_dumps': True,
                        'sharded_tests': sharded_tests,
                        'browser_total_shards': 3, 'browser_shard_index': 2,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

# B('XP Tests (3)', 'rel_unit_3', 'testers|windows', 'win_rel_trigger',
#   auto_reboot=True, notify_on_missing=True)
F('rel_unit_3', win_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=[
      'browser_tests',
      'unit',
    ],
    factory_properties={'process_dumps': True,
                        'sharded_tests': sharded_tests,
                        'browser_total_shards': 3, 'browser_shard_index': 3,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

# B('Vista Tests (1)', 'rel_unit_1', 'testers|windows', 'win_rel_trigger',
#   auto_reboot=True, notify_on_missing=True)
# B('Vista Tests (2)', 'rel_unit_2', 'testers|windows', 'win_rel_trigger',
#   auto_reboot=True, notify_on_missing=True)
# B('Vista Tests (3)', 'rel_unit_3', 'testers|windows', 'win_rel_trigger',
#   auto_reboot=True, notify_on_missing=True)
# B('Win7 Tests (1)', 'rel_unit_1', 'testers|windows', 'win_rel_trigger',
#   auto_reboot=True, notify_on_missing=True)
# B('Win7 Tests (2)', 'rel_unit_2', 'testers|windows', 'win_rel_trigger',
#   auto_reboot=True, notify_on_missing=True)
# B('Win7 Tests (3)', 'rel_unit_3', 'testers|windows', 'win_rel_trigger',
#   auto_reboot=True, notify_on_missing=True)

# B('Win7 Sync', 'rel_sync', 'testers|windows', 'win_rel_trigger',
#   notify_on_missing=True)
F('rel_sync', win_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=['sync_integration'],
    factory_properties={'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

# B('NACL Tests', 'rel_nacl', 'testers|windows', 'win_rel_trigger',
#   notify_on_missing=True)
F('rel_nacl', win_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=['nacl_integration'],
    factory_properties={'process_dumps': True,
                        'start_crash_handler': True,}))

# B('NACL Tests (x64)', 'rel_nacl', 'testers|windows', 'win_rel_trigger',
#   notify_on_missing=True)

# B('Chrome Frame Tests (ie6)', 'rel_cf', 'testers|windows', 'win_rel_trigger',
#   auto_reboot=True, notify_on_missing=True)
F('rel_cf', win_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=[
      'chrome_frame_tests',
      'chrome_frame_net_tests',
      'chrome_frame_unittests',
    ],
    factory_properties={'process_dumps': True,
                        'start_crash_handler': True,}))

# B('Chrome Frame Tests (ie7)', 'rel_cf', 'testers|windows', 'win_rel_trigger',
#   auto_reboot=True, notify_on_missing=True)
# B('Chrome Frame Tests (ie8)', 'rel_cf', 'testers|windows', 'win_rel_trigger',
#   auto_reboot=True, notify_on_missing=True)

################################################################################
## Debug
################################################################################

dbg_archive = ''
# dbg_archive = master_config.GetArchiveUrl('Chromium', 'Win Builder (dbg)',
#                                           'cr-win-dbg', 'win32')

#
# Main debug scheduler for src/
#
S('win_dbg', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the dbg builder
#
T('win_dbg_trigger')

#
# Win Dbg 2008 Builder
#
# B('Win Builder 2008 (dbg)', 'dbg_2008', 'compile|windows', 'win_dbg',
#   builddir='cr-win-2008-dbg', notify_on_missing=True)
F('dbg_2008', win().ChromiumFactory(
    target='Debug',
    slave_type='Builder',
    project='all.sln;chromium_builder_tests',
    factory_properties={'gclient_env': {
        'GYP_MSVS_VERSION': '2008',
        'GYP_DEFINES': 'fastbuild=1'}}))

#
# Win Dbg Builder
#
# B('Win Builder (dbg)', 'dbg', 'compile|windows', 'win_dbg',
#   builddir='cr-win-dbg', notify_on_missing=True)
F('dbg', win().ChromiumFactory(
    target='Debug',
    slave_type='Builder',
    project='all.sln;chromium_builder_tests',
    factory_properties={'gclient_env': {'GYP_DEFINES': 'fastbuild=1'},
                        'trigger': 'win_dbg_trigger'}))

#
# Win Dbg Unit testers
#
# B('XP Tests (dbg)(1)', 'dbg_unit_1', 'testers|windows', 'win_dbg_trigger',
#   auto_reboot=True, notify_on_missing=True)
F('dbg_unit_1', win_tester().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=[
      'base',
      'cacheinvalidation',
      'check_deps',
      'courgette',
      'crypto',
      'googleurl',
      'gpu',
      'installer',
      'jingle',
      'media',
      'printing',
      'remoting',
      'safe_browsing',
      'unit',
    ],
    factory_properties={'process_dumps': True,
                        'sharded_tests': sharded_tests,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))


# B('XP Tests (dbg)(2)', 'dbg_unit_2', 'testers|windows', 'win_dbg_trigger',
#   auto_reboot=True, notify_on_missing=True)
F('dbg_unit_2', win_tester().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=[
      'browser_tests',
      'net',
    ],
    factory_properties={'sharded_tests': sharded_tests,
                        'browser_total_shards': 5, 'browser_shard_index': 1,
                        'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

# B('XP Tests (dbg)(3)', 'dbg_unit_3', 'testers|windows', 'win_dbg_trigger',
#   auto_reboot=True, notify_on_missing=True)
F('dbg_unit_3', win_tester().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=[
      'browser_tests',
      'sandbox',
    ],
    factory_properties={'sharded_tests': sharded_tests,
                        'browser_total_shards': 5, 'browser_shard_index': 2,
                        'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

# B('XP Tests (dbg)(4)', 'dbg_unit_4', 'testers|windows', 'win_dbg_trigger',
#   auto_reboot=True, notify_on_missing=True)
F('dbg_unit_4', win_tester().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['browser_tests'],
    factory_properties={'sharded_tests': sharded_tests,
                        'browser_total_shards': 5, 'browser_shard_index': 3,
                        'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

# B('XP Tests (dbg)(5)', 'dbg_unit_5', 'testers|windows', 'win_dbg_trigger',
#   auto_reboot=True, notify_on_missing=True)
F('dbg_unit_5', win_tester().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['browser_tests'],
    factory_properties={'sharded_tests': sharded_tests,
                        'browser_total_shards': 5, 'browser_shard_index': 4,
                        'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

# B('XP Tests (dbg)(6)', 'dbg_unit_6', 'testers|windows', 'win_dbg_trigger',
#   auto_reboot=True, notify_on_missing=True)
F('dbg_unit_6', win_tester().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['browser_tests'],
    factory_properties={'sharded_tests': sharded_tests,
                        'browser_total_shards': 5, 'browser_shard_index': 5,
                        'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

# B('Win7 Tests (dbg)(1)', 'dbg_unit_1', 'testers|windows', 'win_dbg_trigger',
#   auto_reboot=True, notify_on_missing=True)
# B('Win7 Tests (dbg)(2)', 'dbg_unit_2', 'testers|windows', 'win_dbg_trigger',
#   auto_reboot=True, notify_on_missing=True)
# B('Win7 Tests (dbg)(3)', 'dbg_unit_3', 'testers|windows', 'win_dbg_trigger',
#   auto_reboot=True, notify_on_missing=True)
# B('Win7 Tests (dbg)(4)', 'dbg_unit_4', 'testers|windows', 'win_dbg_trigger',
#   auto_reboot=True, notify_on_missing=True)
# B('Win7 Tests (dbg)(5)', 'dbg_unit_5', 'testers|windows', 'win_dbg_trigger',
#   auto_reboot=True, notify_on_missing=True)
# B('Win7 Tests (dbg)(6)', 'dbg_unit_6', 'testers|windows', 'win_dbg_trigger',
#   auto_reboot=True, notify_on_missing=True)

#
# Win Dbg Interactive Tests
#
# B('Interactive Tests (dbg)', 'dbg_int', 'testers|windows', 'win_dbg_trigger',
#   notify_on_missing=True)
F('dbg_int', win_tester().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['interactive_ui'],
    factory_properties={'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

#
# Dbg Aura builder
#
aura_gyp_defines = 'use_aura=1 fastbuild=1'
# B('Win Aura', 'dbg_aura', 'compile|testers|windows', 'win_dbg',
#   notify_on_missing=True)
F('dbg_aura', win().ChromiumFactory(
    target='Debug',
    slave_type='BuilderTester',
    tests=[
      'aura',
      'aura_shell',
      'compositor',
      'views',
    ],
    project='all.sln;aura_builder',
      factory_properties={'gclient_env': {'GYP_DEFINES': aura_gyp_defines},
                          'process_dumps': True,
                          'start_crash_handler': True,
                          'generate_gtest_json': True}))
# When the tests grow we'll need a separate tester.

def Update(config, active_master, c):
  return helper.Update(c)
