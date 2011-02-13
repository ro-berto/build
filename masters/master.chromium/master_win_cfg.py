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

def win(): return chromium_factory.ChromiumFactory('src/build', 'win32')


################################################################################
## Release
################################################################################

defaults['category'] = '2windows'

# Archive location
rel_archive = master_config.GetArchiveUrl('Chromium', 'Win Builder',
                                          'cr-win-rel', 'win32')

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
B('Win Builder', 'rel', 'compile|windows', 'win_rel', builddir='cr-win-rel')
F('rel', win().ChromiumFactory(
    slave_type='Builder',
    project='all.sln;chromium_builder_tests',
    factory_properties={'trigger': 'win_rel_trigger'}))

#
# Win Rel testers
#
B('XP Tests (1)', 'rel_unit_1', 'testers|windows', 'win_rel_trigger',
  auto_reboot=True)
F('rel_unit_1', win().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=['unit', 'media', 'printing', 'remoting', 'gpu', 'browser_tests',
           'courgette', 'googleurl', 'safe_browsing', 'sandbox'],
    factory_properties={'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

B('XP Tests (2)', 'rel_unit_2', 'testers|windows', 'win_rel_trigger',
  auto_reboot=True)
F('rel_unit_2', win().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=['ui', 'installer', 'base', 'net'],
    factory_properties={'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

B('Vista Tests (1)', 'rel_unit_1', 'testers|windows', 'win_rel_trigger',
  auto_reboot=True)
B('Vista Tests (2)', 'rel_unit_2', 'testers|windows', 'win_rel_trigger',
  auto_reboot=True)

B('Win7 Sync', 'rel_sync', 'testers|windows', 'win_rel_trigger')
F('rel_sync', win().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=['sync_integration'],
    factory_properties={'process_dumps': True,
                        'start_crash_handler': True,}))

B('NACL Tests', 'rel_nacl', 'testers|windows', 'win_rel_trigger')
F('rel_nacl', win().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=['nacl_ui', 'nacl_sandbox'],
    factory_properties={'process_dumps': True,
                        'start_crash_handler': True,}))

B('NACL Tests (x64)', 'rel_nacl', 'testers|windows', 'win_rel_trigger')

B('Chrome Frame Tests (ie6)', 'rel_cf', 'testers|windows', 'win_rel_trigger',
  auto_reboot=True)
F('rel_cf', win().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=['chrome_frame'],
    factory_properties={'process_dumps': True,
                        'start_crash_handler': True,}))

B('Chrome Frame Tests (ie7)', 'rel_cf', 'testers|windows', 'win_rel_trigger',
  auto_reboot=True)
B('Chrome Frame Tests (ie8)', 'rel_cf', 'testers|windows', 'win_rel_trigger',
  auto_reboot=True)

################################################################################
## Debug
################################################################################

dbg_archive = master_config.GetArchiveUrl('Chromium', 'Win Builder (dbg)',
                                          'cr-win-dbg', 'win32')

#
# Main debug scheduler for src/
#
S('win_dbg', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the dbg builder
#
T('win_dbg_trigger')

#
# Win Dbg Builder
#
B('Win Builder (dbg)', 'dbg', 'compile|windows', 'win_dbg',
  builddir='cr-win-dbg')
F('dbg', win().ChromiumFactory(
    target='Debug',
    slave_type='Builder',
    project='all.sln;chromium_builder_tests',
    factory_properties={'gclient_env': {'GYP_DEFINES': 'fastbuild=1'},
                        'trigger': 'win_dbg_trigger'}))

#
# Win Dbg Unit testers
#
B('XP Tests (dbg)(1)', 'dbg_unit_1', 'testers|windows', 'win_dbg_trigger',
  auto_reboot=True)
F('dbg_unit_1', win().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['check_deps', 'googleurl', 'media', 'printing', 'remoting',
           'courgette', 'unit', 'gpu', 'installer', 'safe_browsing',
           'base'],
    factory_properties={'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))


B('XP Tests (dbg)(2)', 'dbg_unit_2', 'testers|windows', 'win_dbg_trigger',
  auto_reboot=True)
F('dbg_unit_2', win().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['ui', 'net', 'browser_tests'],
    factory_properties={'ui_total_shards': 4, 'ui_shard_index': 1,
                        'browser_total_shards': 4, 'browser_shard_index': 1,
                        'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

B('XP Tests (dbg)(3)', 'dbg_unit_3', 'testers|windows', 'win_dbg_trigger',
  auto_reboot=True)
F('dbg_unit_3', win().ChromiumFactory(
      target='Debug',
      slave_type='Tester',
      build_url=dbg_archive,
      tests=['ui', 'sandbox', 'browser_tests'],
      factory_properties={'ui_total_shards': 4, 'ui_shard_index': 2,
                          'browser_total_shards': 4, 'browser_shard_index': 2,
                          'process_dumps': True,
                          'start_crash_handler': True,
                          'generate_gtest_json': True}))

B('XP Tests (dbg)(4)', 'dbg_unit_4', 'testers|windows', 'win_dbg_trigger',
  auto_reboot=True)
F('dbg_unit_4', win().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['ui', 'browser_tests'],
    factory_properties={'ui_total_shards': 4, 'ui_shard_index': 3,
                        'browser_total_shards': 4, 'browser_shard_index': 3,
                        'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

B('XP Tests (dbg)(5)', 'dbg_unit_5', 'testers|windows', 'win_dbg_trigger',
  auto_reboot=True)
F('dbg_unit_5', win().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['ui', 'browser_tests'],
    factory_properties={'ui_total_shards': 4, 'ui_shard_index': 4,
                        'browser_total_shards': 4, 'browser_shard_index': 4,
                        'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

B('Vista Tests (dbg)(1)', 'dbg_unit_1', 'testers|windows', 'win_dbg_trigger',
  auto_reboot=True)
B('Vista Tests (dbg)(2)', 'dbg_unit_2', 'testers|windows', 'win_dbg_trigger',
  auto_reboot=True)
B('Vista Tests (dbg)(3)', 'dbg_unit_3', 'testers|windows', 'win_dbg_trigger',
  auto_reboot=True)
B('Vista Tests (dbg)(4)', 'dbg_unit_4', 'testers|windows', 'win_dbg_trigger',
  auto_reboot=True)
B('Vista Tests (dbg)(5)', 'dbg_unit_5', 'testers|windows', 'win_dbg_trigger',
  auto_reboot=True)

#
# Win Dbg Interactive Tests
#
B('Interactive Tests (dbg)', 'dbg_int', 'testers|windows', 'win_dbg_trigger')
F('dbg_int', win().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['interactive_ui'],
    factory_properties={'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

#
# Dbg Shared builder
#
B('Win Builder (dbg)(shared)', 'dbg_shared', 'compile|windows', 'win_dbg')
F('dbg_shared', win().ChromiumFactory(
    target='Debug',
    slave_type='Builder',
    project='all.sln',
    factory_properties={'gclient_env':
        {'GYP_DEFINES' : 'component=shared_library fastbuild=1'}}))

def Update(config, active_master, c):
  return helper.Update(c)
