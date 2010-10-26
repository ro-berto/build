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
# Dependent scheduler for the dbg builder
#
D('win_rel_dep', 'win_rel')

#
# Win Rel Builder
#
B('Win Builder', 'rel', 'compile|windows', 'win_rel', builddir='cr-win-rel')
F('rel', win().ChromiumFactory(
    'chromium-win-rel',
    slave_type='Builder',
    project='all.sln;chromium_builder_tests'))

#
# Win Rel testers
#
B('XP Tests', 'rel_unit', 'testers|windows', 'win_rel_dep')
F('rel_unit', win().ChromiumFactory(
    'chromium-win-rel',
    slave_type='Tester',
    build_url=rel_archive,
    tests=['unit', 'ui', 'media', 'printing', 'remoting', 'gpu',
           'browser_tests', 'courgette', 'googleurl', 'installer',
           'safe_browsing', 'base', 'net', 'sandbox'],
    factory_properties={'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

B('Vista Tests', 'rel_unit', 'testers|windows', 'win_rel_dep', auto_reboot=True)

B('NACL Tests', 'rel_nacl', 'testers|windows', 'win_rel_dep')
F('rel_nacl', win().ChromiumFactory(
    'chromium-win-rel',
    slave_type='Tester',
    build_url=rel_archive,
    tests=['nacl_ui', 'nacl_sandbox'],
    factory_properties={'process_dumps': True,
                        'start_crash_handler': True,}))

B('NACL Tests (x64)', 'rel_nacl', 'testers|windows', 'win_rel_dep')

B('Chrome Frame Tests (ie6)', 'rel_cf', 'testers|windows', 'win_rel_dep')
F('rel_cf', win().ChromiumFactory(
    'chromium-win-rel',
    slave_type='Tester',
    build_url=rel_archive,
    tests=['chrome_frame'],
    factory_properties={'process_dumps': True,
                        'start_crash_handler': True,}))

B('Chrome Frame Tests (ie7)', 'rel_cf', 'testers|windows', 'win_rel_dep')
B('Chrome Frame Tests (ie8)', 'rel_cf', 'testers|windows', 'win_rel_dep')

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
# Dependent scheduler for the dbg builder
#
D('win_dbg_dep', 'win_dbg')

#
# Win Dbg Builder
#
B('Win Builder (dbg)', 'dbg', 'compile|windows', 'win_dbg',
  builddir='cr-win-dbg')
F('dbg', win().ChromiumFactory(
    'chromium-win-dbg',
    target='Debug',
    slave_type='Builder',
    project='all.sln;chromium_builder_tests'))

#
# Win Dbg Unit testers
#
B('XP Tests (dbg)(1)', 'dbg_unit_1', 'testers|windows', 'win_dbg_dep')
F('dbg_unit_1', win().ChromiumFactory(
    'chromium-win-dbg',
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['check_deps', 'googleurl', 'media', 'printing', 'remoting',
           'courgette', 'unit', 'gpu', 'installer', 'safe_browsing',
           'base'],
    factory_properties={'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))


B('XP Tests (dbg)(2)', 'dbg_unit_2', 'testers|windows', 'win_dbg_dep')
F('dbg_unit_2', win().ChromiumFactory(
    'chromium-win-dbg',
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['ui', 'net'],
    factory_properties={'ui_total_shards': 3, 'ui_shard_index': 1,
                        'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

B('XP Tests (dbg)(3)', 'dbg_unit_3', 'testers|windows', 'win_dbg_dep')
F('dbg_unit_3', win().ChromiumFactory(
      'chromium-win-dbg',
      target='Debug',
      slave_type='Tester',
      build_url=dbg_archive,
      tests=['ui', 'sandbox'],
      factory_properties={'ui_total_shards': 3, 'ui_shard_index': 2,
                          'process_dumps': True,
                          'start_crash_handler': True,
                          'generate_gtest_json': True}))

B('XP Tests (dbg)(4)', 'dbg_unit_4', 'testers|windows', 'win_dbg_dep')
F('dbg_unit_4', win().ChromiumFactory(
    'chromium-win-dbg',
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['ui', 'browser_tests'],
    factory_properties={'ui_total_shards': 3, 'ui_shard_index': 3,
                        'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

B('Vista Tests (dbg)(1)', 'dbg_unit_1', 'testers|windows', 'win_dbg_dep',
  auto_reboot=True)
B('Vista Tests (dbg)(2)', 'dbg_unit_2', 'testers|windows', 'win_dbg_dep',
  auto_reboot=True)
B('Vista Tests (dbg)(3)', 'dbg_unit_3', 'testers|windows', 'win_dbg_dep',
  auto_reboot=True)
B('Vista Tests (dbg)(4)', 'dbg_unit_4', 'testers|windows', 'win_dbg_dep',
  auto_reboot=True)

#
# Win Dbg Interactive Tests
#
B('Interactive Tests (dbg)', 'dbg_int', 'testers|windows', 'win_dbg_dep')
F('dbg_int', win().ChromiumFactory(
    'chromium-win-dbg',
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['interactive_ui'],
    factory_properties={'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

def Update(config, active_master, c):
  return helper.Update(c)
