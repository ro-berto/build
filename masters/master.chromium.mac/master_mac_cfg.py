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

def mac():
  return chromium_factory.ChromiumFactory('src/build', 'darwin')
def mac_tester():
  return chromium_factory.ChromiumFactory(
      'src/build', 'darwin', nohooks_on_update=True)

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

defaults['category'] = '3mac'

# Archive location
rel_archive = ''
# rel_archive = master_config.GetArchiveUrl('Chromium', 'Mac Builder',
#                                           'cr-mac-rel', 'mac')

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
# B('Mac Builder', 'rel', 'compile', 'mac_rel', builddir='cr-mac-rel',
#   notify_on_missing=True)
F('rel', mac().ChromiumFactory(
    slave_type='Builder',
    options=[
        '--compiler=goma-clang', '--', '-target', 'chromium_builder_tests'],
    factory_properties={
        'trigger': 'mac_rel_trigger',
    }))

#
# Mac Rel testers
#
# B('Mac10.6 Tests (1)', 'rel_unit_1', 'testers', 'mac_rel_trigger',
#   auto_reboot=True, notify_on_missing=True)
F('rel_unit_1', mac_tester().ChromiumFactory(
  slave_type='Tester',
  build_url=rel_archive,
  tests=[
    'base',
    'browser_tests',
    'cacheinvalidation',
    'crypto',
    'googleurl',
    'gpu',
    'jingle',
    'media',
    'nacl_integration',
    'printing',
    'remoting',
    'safe_browsing',
  ],
  factory_properties={'generate_gtest_json': True,
                      'sharded_tests': sharded_tests,
                      'browser_total_shards': 3, 'browser_shard_index': 1,})
)

# B('Mac10.6 Tests (2)', 'rel_unit_2', 'testers', 'mac_rel_trigger',
#   auto_reboot=True, notify_on_missing=True)
F('rel_unit_2', mac_tester().ChromiumFactory(
  slave_type='Tester',
  build_url=rel_archive,
  tests=[
    'browser_tests',
    'unit',
  ],
  factory_properties={'generate_gtest_json': True,
                      'sharded_tests': sharded_tests,
                      'browser_total_shards': 3, 'browser_shard_index': 2,})
)

# B('Mac10.6 Tests (3)', 'rel_unit_3', 'testers', 'mac_rel_trigger',
#   auto_reboot=True, notify_on_missing=True)
F('rel_unit_3', mac_tester().ChromiumFactory(
  slave_type='Tester',
  build_url=rel_archive,
  tests=[
    'browser_tests',
    'net',
  ],
  factory_properties={'generate_gtest_json': True,
                      'sharded_tests': sharded_tests,
                      'browser_total_shards': 3, 'browser_shard_index': 3,})
)

## B('Mac10.7 Tests (1)', 'rel_unit_1', 'testers', 'mac_rel_trigger',
##   auto_reboot=True, notify_on_missing=True)
## B('Mac10.7 Tests (2)', 'rel_unit_2', 'testers', 'mac_rel_trigger',
##   auto_reboot=True, notify_on_missing=True)
## B('Mac10.7 Tests (3)', 'rel_unit_3', 'testers', 'mac_rel_trigger',
##   auto_reboot=True, notify_on_missing=True)

# B('Mac10.6 Sync', 'rel_sync', 'testers', 'mac_rel_trigger',
#   auto_reboot=True, notify_on_missing=True)
F('rel_sync', mac_tester().ChromiumFactory(
  slave_type='Tester',
  build_url=rel_archive,
  tests=['sync_integration'],
  factory_properties={'generate_gtest_json': True}))

################################################################################
## Debug
################################################################################

# Archive location
dbg_archive = ''
# dbg_archive = master_config.GetArchiveUrl('Chromium', 'Mac Builder (dbg)',
#                                           'Mac_Builder__dbg_', 'mac')

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
# B('Mac Builder (dbg)', 'dbg', 'compile', 'mac_dbg', notify_on_missing=True)
F('dbg', mac().ChromiumFactory(
    target='Debug',
    slave_type='Builder',
    options=[
        '--compiler=goma-clang', '--build-tool=ninja', '--',
        'chromium_builder_tests'],
    factory_properties={
        'trigger': 'mac_dbg_trigger',
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
            'GYP_DEFINES':'clang=1 clang_use_chrome_plugins=1'
        },
    }))

#
# Mac Dbg Unit testers
#

# B('Mac 10.6 Tests (dbg)(1)', 'dbg_unit_1', 'testers', 'mac_dbg_trigger',
#   auto_reboot=True, notify_on_missing=True)
F('dbg_unit_1', mac_tester().ChromiumFactory(
  slave_type='Tester',
  build_url=dbg_archive,
  target='Debug',
  tests=[
    'browser_tests',
    'cacheinvalidation',
    'crypto',
    'googleurl',
    'gpu',
    'jingle',
    'nacl_integration',
    'printing',
    'remoting',
    'safe_browsing',
  ],
  factory_properties={'generate_gtest_json': True,
                      'sharded_tests': sharded_tests,
                      'browser_total_shards': 4, 'browser_shard_index': 1,}))

# B('Mac 10.6 Tests (dbg)(2)', 'dbg_unit_2', 'testers', 'mac_dbg_trigger',
#   auto_reboot=True, notify_on_missing=True)
F('dbg_unit_2', mac_tester().ChromiumFactory(
  slave_type='Tester',
  build_url=dbg_archive,
  target='Debug',
  tests=[
    'browser_tests',
    'check_deps',
    'media',
    'net',
  ],
  factory_properties={'generate_gtest_json': True,
                      'sharded_tests': sharded_tests,
                      'browser_total_shards': 4, 'browser_shard_index': 2,}))

# B('Mac 10.6 Tests (dbg)(3)', 'dbg_unit_3', 'testers', 'mac_dbg_trigger',
#   auto_reboot=True, notify_on_missing=True)
F('dbg_unit_3', mac_tester().ChromiumFactory(
  slave_type='Tester',
  build_url=dbg_archive,
  target='Debug',
  tests=[
    'base',
    'browser_tests',
    'interactive_ui',
  ],
  factory_properties={'generate_gtest_json': True,
                      'sharded_tests': sharded_tests,
                      'browser_total_shards': 4, 'browser_shard_index': 3,}))

# B('Mac 10.6 Tests (dbg)(4)', 'dbg_unit_4', 'testers', 'mac_dbg_trigger',
#   auto_reboot=True, notify_on_missing=True)
F('dbg_unit_4', mac_tester().ChromiumFactory(
  slave_type='Tester',
  build_url=dbg_archive,
  target='Debug',
  tests=[
    'browser_tests',
    'unit',
  ],
  factory_properties={'generate_gtest_json': True,
                      'sharded_tests': sharded_tests,
                      'browser_total_shards': 4, 'browser_shard_index': 4,}))

## B('Mac 10.7 Tests (dbg)(1)', 'dbg_unit_1', 'testers', 'mac_dbg_trigger',
##   auto_reboot=True, notify_on_missing=True)
## B('Mac 10.7 Tests (dbg)(2)', 'dbg_unit_2', 'testers', 'mac_dbg_trigger',
##   auto_reboot=True, notify_on_missing=True)
## B('Mac 10.7 Tests (dbg)(3)', 'dbg_unit_3', 'testers', 'mac_dbg_trigger',
##   auto_reboot=True, notify_on_missing=True)
## B('Mac 10.7 Tests (dbg)(4)', 'dbg_unit_4', 'testers', 'mac_dbg_trigger',
##   auto_reboot=True, notify_on_missing=True)


def Update(config, active_master, c):
  return helper.Update(c)
