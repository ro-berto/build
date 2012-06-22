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

def linux():
  return chromium_factory.ChromiumFactory('src/build', 'linux2')
def linux_tester():
  return chromium_factory.ChromiumFactory(
      'src/build', 'linux2', nohooks_on_update=True)

# Tests that are single-machine shard-safe. For now we only use the sharding
# supervisor for long tests (more than 30 seconds) that are known to be stable.
sharded_tests = [
  'base_unittests',
  'browser_tests',
  'media_unittests',
]

# These are the common targets to most of the builders
linux_all_test_targets = [
  'base_unittests',
  'browser_tests',
  'cacheinvalidation_unittests',
  'content_unittests',
  'crypto_unittests',
  'dbus_unittests',
  'googleurl_unittests',
  'gpu_unittests',
  'ipc_tests',
  'jingle_unittests',
  'media_unittests',
  'net_unittests',
  'printing_unittests',
  'remoting_unittests',
  'safe_browsing_tests',
  'sql_unittests',
  'sync_unit_tests',
  'ui_unittests',
  'unit_tests',
]


################################################################################
## Release
################################################################################

defaults['category'] = '4linux'

rel_archive = ''
# rel_archive = master_config.GetArchiveUrl('Chromium', 'Linux Builder x64',
#                                           'Linux_Builder_x64', 'linux')
#
# Main release scheduler for src/
#
S('linux_rel', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the rel builder
#
T('linux_rel_trigger')

#
# Linux Rel Builder
#
# B('Linux Builder x64', 'rel', 'compile', 'linux_rel', notify_on_missing=True)
F('rel', linux().ChromiumFactory(
    slave_type='Builder',
    options=['--compiler=goma',] + linux_all_test_targets +
            ['sync_integration_tests'],
    tests=['check_deps'],
    factory_properties={'trigger': 'linux_rel_trigger'}))

#
# Linux Rel testers
#
# B('Linux Tests x64', 'rel_unit', 'testers', 'linux_rel_trigger',
#   auto_reboot=True, notify_on_missing=True)
F('rel_unit', linux_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=[
      'base',
      'browser_tests',
      'cacheinvalidation',
      'crypto',
      'dbus',
      'googleurl',
      'gpu',
      'jingle',
      'media',
      'net',
      'printing',
      'remoting',
      'safe_browsing',
      'unit',
    ],
    factory_properties={'sharded_tests': sharded_tests,
                        'generate_gtest_json': True}))

# B('Linux Sync', 'rel_sync', 'testers', 'linux_rel_trigger', auto_reboot=True,
#   notify_on_missing=True)
F('rel_sync', linux_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=['sync_integration'],
    factory_properties={'generate_gtest_json': True}))

#
# Linux aura bot
#

# Interactive ui tests and browser tests disabled in this configuration; it's a
# long term goal to support them, but that isn't happening on the order of
# months due to manpower issues.
linux_aura_tests = [
  'aura',
  'base',
  #'browser_tests',
  'cacheinvalidation',
  'compositor',
  'crypto',
  'googleurl',
  'gpu',
  #'interactive_ui',
  'jingle',
  'media',
  'net',
  'printing',
  'remoting',
  'views',
  'unit',
]

linux_aura_options=[
  'aura_builder',
  'base_unittests',
  'browser_tests',
  'cacheinvalidation_unittests',
  'compositor_unittests',
  'content_unittests',
  'crypto_unittests',
  'googleurl_unittests',
  'gpu_unittests',
  'interactive_ui_tests',
  'ipc_tests',
  'jingle_unittests',
  'net_unittests',
  'media_unittests',
  'printing_unittests',
  'remoting_unittests',
  'safe_browsing_tests',
  'sql_unittests',
  'ui_unittests',
]

# B('Linux (aura)', 'f_linux_rel_aura', 'compile', 'linux_rel',
#   notify_on_missing=True)
F('f_linux_rel_aura', linux().ChromiumFactory(
    target='Release',
    slave_type='BuilderTester',
    options=['--compiler=goma'] + linux_aura_options,
    tests=linux_aura_tests,
    factory_properties={'gclient_env': {'GYP_DEFINES': 'use_aura=1'}}))


################################################################################
## Debug
################################################################################

#
# Main debug scheduler for src/
#
S('linux_dbg', branch='src', treeStableTimer=60)

dbg_archive = ''
# dbg_archive = master_config.GetArchiveUrl('Chromium', 'Linux Builder (dbg)',
#                                           'Linux_Builder__dbg_', 'linux')

#
# Triggerable scheduler for the dbg builders
#
T('linux_dbg_trigger')

#
# Linux Dbg Builder
#
#B('Linux Builder (dbg)', 'dbg', 'compile', 'linux_dbg', notify_on_missing=True)
F('dbg', linux().ChromiumFactory(
    slave_type='Builder',
    target='Debug',
    options=['--compiler=goma',] + linux_all_test_targets + [
             'interactive_ui_tests',
           ],
    factory_properties={'trigger': 'linux_dbg_trigger',
                        'gclient_env': {'GYP_DEFINES':'target_arch=ia32'},}))

#
# Linux Dbg Unit testers
#

# B('Linux Tests (dbg)(1)', 'dbg_unit_1', 'testers', 'linux_dbg_trigger',
#   auto_reboot=True, notify_on_missing=True)
F('dbg_unit_1', linux_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=dbg_archive,
    target='Debug',
    tests=[
      'browser_tests',
      'net',
    ],
    factory_properties={'sharded_tests': sharded_tests,
                        'generate_gtest_json': True}))

# B('Linux Tests (dbg)(2)', 'dbg_unit_2', 'testers', 'linux_dbg_trigger',
#   auto_reboot=True, notify_on_missing=True)
F('dbg_unit_2', linux_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=dbg_archive,
    target='Debug',
    tests=[
      'base',
      'cacheinvalidation',
      'crypto',
      'dbus',
      'googleurl',
      'gpu',
      'interactive_ui',
      'jingle',
      'media',
      'nacl_integration',
      'printing',
      'remoting',
      'safe_browsing',
      'unit',
    ],
    factory_properties={'sharded_tests': sharded_tests,
                        'generate_gtest_json': True}))

#
# Linux Dbg Clang bot
#

# B('Linux Clang (dbg)', 'dbg_linux_clang', 'compile', 'linux_dbg',
#   notify_on_missing=True)
F('dbg_linux_clang', linux().ChromiumFactory(
    target='Debug',
    options=['--build-tool=make', '--compiler=goma-clang'],
    tests=[
      'base',
      'crypto',
      'gfx',
      'unit',
    ],
    factory_properties={
      'gclient_env': {
        'GYP_DEFINES':
          'clang=1 clang_use_chrome_plugins=1 fastbuild=1 '
            'test_isolation_mode=noop',
    }}))


def Update(config, active_master, c):
  return helper.Update(c)
