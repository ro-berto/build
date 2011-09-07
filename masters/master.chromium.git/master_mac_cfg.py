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
builddir = 'cr-mac-rel-git'
rel_archive = master_config.GetArchiveUrl('ChromiumGIT',
                                          'Mac Builder (git)',
                                          builddir,
                                          'mac')

#
# Main debug scheduler for src/
#
S('mac_rel', branch='master', treeStableTimer=60)

#
# Triggerable scheduler for the dbg builder
#
T('mac_rel_trigger')

#
# Mac Rel Builder
#
B('Mac Builder (git)', 'rel', 'compile', 'mac_rel', builddir=builddir)
F('rel', mac().ChromiumGITFactory(
    slave_type='Builder',
    options=['--', '-target', 'chromium_builder_tests'],
    factory_properties={'trigger': 'mac_rel_trigger'}))

#
# Mac Rel testers
#
B('Mac10.5 Tests (1)', 'rel_unit_1', 'testers', 'mac_rel_trigger')
F('rel_unit_1', mac().ChromiumGITFactory(
  slave_type='Tester',
  build_url=rel_archive,
  tests=['base',
         'browser_tests',
         'cacheinvalidation',
         'crypto',
         'googleurl',
         'gpu',
         'jingle',
         'media',
         'nacl_integration',
         'nacl_sandbox',
         'nacl_ui',
         'printing',
         'remoting',
         'safe_browsing',
         'ui'],
  factory_properties={'generate_gtest_json': True,
                      'ui_total_shards': 3, 'ui_shard_index': 1,
                      'browser_total_shards': 3, 'browser_shard_index': 1,})
)

#B('Mac10.5 Tests (2)', 'rel_unit_2', 'testers', 'mac_rel_trigger')
#F('rel_unit_2', mac().ChromiumGITFactory(
#  slave_type='Tester',
#  build_url=rel_archive,
#  tests=['browser_tests', 'ui', 'unit'],
#  factory_properties={'generate_gtest_json': True,
#                      'ui_total_shards': 3, 'ui_shard_index': 2,
#                      'browser_total_shards': 3, 'browser_shard_index': 2,})
#)
#
#B('Mac10.5 Tests (3)', 'rel_unit_3', 'testers', 'mac_rel_trigger')
#F('rel_unit_3', mac().ChromiumGITFactory(
#  slave_type='Tester',
#  build_url=rel_archive,
#  tests=['browser_tests', 'net', 'ui'],
#  factory_properties={'generate_gtest_json': True,
#                      'ui_total_shards': 3, 'ui_shard_index': 3,
#                      'browser_total_shards': 3, 'browser_shard_index': 3,})
#)
#
#B('Mac10.6 Tests (1)', 'rel_unit_1', 'testers', 'mac_rel_trigger')
#B('Mac10.6 Tests (2)', 'rel_unit_2', 'testers', 'mac_rel_trigger')
#B('Mac10.6 Tests (3)', 'rel_unit_3', 'testers', 'mac_rel_trigger')
#
#B('Mac10.6 Sync', 'rel_sync', 'testers', 'mac_rel_trigger')
#F('rel_sync', mac().ChromiumGITFactory(
#  slave_type='Tester',
#  build_url=rel_archive,
#  tests=['sync_integration'],
#  factory_properties={'generate_gtest_json': True}))
#
#################################################################################
### Debug
#################################################################################
#
## Archive location
#dbg_archive = master_config.GetArchiveUrl('Chromium', 'Mac Builder (dbg)',
#                                          'Mac_Builder__dbg_', 'mac')
#
##
## Main debug scheduler for src/
##
#S('mac_dbg', branch='src', treeStableTimer=60)
#
##
## Triggerable scheduler for the dbg builder
##
#T('mac_dbg_trigger')
#
##
## Mac Dbg Builder
##
#B('Mac Builder (dbg)', 'dbg', 'compile', 'mac_dbg')
#F('dbg', mac().ChromiumGITFactory(
#    target='Debug',
#    slave_type='Builder',
#    options=['--', '-target', 'chromium_builder_tests'],
#    factory_properties={'trigger': 'mac_dbg_trigger'}))
#
##
## Mac Dbg Unit testers
##
#
#B('Mac 10.5 Tests (dbg)(1)', 'dbg_unit_1', 'testers', 'mac_dbg_trigger',
#  auto_reboot=True)
#F('dbg_unit_1', mac().ChromiumGITFactory(
#  slave_type='Tester',
#  build_url=dbg_archive,
#  target='Debug',
#  tests=['browser_tests',
#         'cacheinvalidation',
#         'check_deps',
#         'crypto',
#         'googleurl',
#         'gpu',
#         'interactive_ui',
#         'jingle',
#         'media',
#         'nacl_integration',
#         'nacl_sandbox',
#         'nacl_ui',
#         'printing',
#         'remoting',
#         'safe_browsing',
#         'ui'],
#  factory_properties={'generate_gtest_json': True,
#                      'ui_total_shards': 4, 'ui_shard_index': 1,
#                      'browser_total_shards': 4, 'browser_shard_index': 1,}))
#
#B('Mac 10.5 Tests (dbg)(2)', 'dbg_unit_2', 'testers', 'mac_dbg_trigger',
#  auto_reboot=True)
#F('dbg_unit_2', mac().ChromiumGITFactory(
#  slave_type='Tester',
#  build_url=dbg_archive,
#  target='Debug',
#  tests=['browser_tests', 'net', 'ui'],
#  factory_properties={'generate_gtest_json': True,
#                      'ui_total_shards': 4, 'ui_shard_index': 2,
#                      'browser_total_shards': 4, 'browser_shard_index': 2,}))
#
#B('Mac 10.5 Tests (dbg)(3)', 'dbg_unit_3', 'testers', 'mac_dbg_trigger',
#  auto_reboot=True)
#F('dbg_unit_3', mac().ChromiumGITFactory(
#  slave_type='Tester',
#  build_url=dbg_archive,
#  target='Debug',
#  tests=['base', 'browser_tests', 'ui'],
#  factory_properties={'generate_gtest_json': True,
#                      'ui_total_shards': 4, 'ui_shard_index': 3,
#                      'browser_total_shards': 4, 'browser_shard_index': 3,}))
#
#B('Mac 10.5 Tests (dbg)(4)', 'dbg_unit_4', 'testers', 'mac_dbg_trigger',
#  auto_reboot=True)
#F('dbg_unit_4', mac().ChromiumGITFactory(
#  slave_type='Tester',
#  build_url=dbg_archive,
#  target='Debug',
#  tests=['browser_tests', 'ui', 'unit'],
#  factory_properties={'generate_gtest_json': True,
#                      'ui_total_shards': 4, 'ui_shard_index': 4,
#                      'browser_total_shards': 4, 'browser_shard_index': 4,}))
#
#B('Mac 10.6 Tests (dbg)(1)', 'dbg_unit_1', 'testers', 'mac_dbg_trigger',
#  auto_reboot=True)
#B('Mac 10.6 Tests (dbg)(2)', 'dbg_unit_2', 'testers', 'mac_dbg_trigger',
#  auto_reboot=True)
#B('Mac 10.6 Tests (dbg)(3)', 'dbg_unit_3', 'testers', 'mac_dbg_trigger',
#  auto_reboot=True)
#B('Mac 10.6 Tests (dbg)(4)', 'dbg_unit_4', 'testers', 'mac_dbg_trigger',
#  auto_reboot=True)
#
##
## Mac Dbg Clang bot
##
#
#B('Mac Clang (dbg)', 'dbg_mac_clang', 'compile', 'mac_dbg')
#F('dbg_mac_clang', mac().ChromiumGITFactory(
#    target='Debug',
#    options=['--compiler=clang'],
#    # Only include test binaries that run reasonably fast and that don't contain
#    # many flaky tests.
#    tests=[
#        'base', 'gfx', 'crypto',
#        # Adds ipc_tests, sync_unit_tests, unit_tests, and sql_unittests
#        # unit_tests is very flaky due to http://crbug.com/60426
#        # TODO(thakis): Re-add this once the bug is fixed.
#        #'unit',
#    ],
#    factory_properties={
#        'gclient_env': {
#            'GYP_DEFINES':'clang=1 clang_use_chrome_plugins=1'
#    }}))


def Update(config, active_master, c):
  return helper.Update(c)
