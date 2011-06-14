# Copyright (c) 2011 The Chromium Authors. All rights reserved.
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
T = helper.Triggerable

def chromeos(): return chromium_factory.ChromiumFactory('src/build', 'linux2')


################################################################################
## Release
################################################################################

defaults['category'] = '8chromiumos'

#
# Main release scheduler for src/
#
S('chromeos_rel', branch='src', treeStableTimer=60)

#
# ChromeOS Rel Builder
#
B('Linux Builder (ChromiumOS)', 'rel', 'compile', 'chromeos_rel')
F('rel', chromeos().ChromiumOSFactory(
    tests=['unit',
           'base',
           'net',
           'googleurl',
           'media',
           'ui',
           'printing',
           'remoting',
           'browser_tests',
           'interactive_ui',
           'views',
           'crypto',
           'cacheinvalidation',
           'jingle'],
    options=['chromeos_builder'],
    factory_properties={
        'archive_build': True,
        'extra_archive_paths': 'chrome/tools/build/chromeos',
        'gclient_env': { 'GYP_DEFINES':'chromeos=1 target_arch=ia32'},
        'generate_gtest_json': True}))


################################################################################
## Debug
################################################################################

#
# Main debug scheduler for src/
#
S('chromeos_dbg', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the builders
#
T('linux_cros_dbg_trigger')
T('linux_views_dbg_trigger')

#
# ChromeOS Dbg Builders and Testers
#
B('Linux Builder (ChromiumOS dbg)', 'cros_dbg', 'compile', 'chromeos_dbg')
F('cros_dbg', chromeos().ChromiumOSFactory(
    slave_type='NASBuilder',
    target='Debug',
    options=['--compiler=goma', 'chromeos_builder'],
    factory_properties={
        'gclient_env': { 'GYP_DEFINES':'chromeos=1 target_arch=ia32'},
        'trigger': 'linux_cros_dbg_trigger'}))

B('Linux Tests (ChromiumOS dbg)(1)', 'cros_dbg_tests_1', 'testers',
  'linux_cros_dbg_trigger')
F('cros_dbg_tests_1', chromeos().ChromiumOSFactory(
    slave_type='NASTester',
    target='Debug',
    tests=['base',
           'browser_tests',
           'crypto',
           'googleurl',
           'interactive_ui',
           'media',
           'printing',
           'remoting',
           'ui',
           'views',
           'cacheinvalidation',
           'jingle'],
    factory_properties={'generate_gtest_json': True,
                        'ui_total_shards': 3, 'ui_shard_index': 1,
                        'browser_total_shards': 3, 'browser_shard_index': 1,}))

B('Linux Tests (ChromiumOS dbg)(2)', 'cros_dbg_tests_2', 'testers',
  'linux_cros_dbg_trigger')
F('cros_dbg_tests_2', chromeos().ChromiumOSFactory(
    slave_type='NASTester',
    target='Debug',
    tests=['browser_tests', 'ui', 'unit',],
    factory_properties={'generate_gtest_json': True,
                        'ui_total_shards': 3, 'ui_shard_index': 2,
                        'browser_total_shards': 3, 'browser_shard_index': 2,}))

B('Linux Tests (ChromiumOS dbg)(3)', 'cros_dbg_tests_3', 'testers',
  'linux_cros_dbg_trigger')
F('cros_dbg_tests_3', chromeos().ChromiumOSFactory(
    slave_type='NASTester',
    target='Debug',
    tests=['browser_tests', 'net', 'ui',],
    factory_properties={'generate_gtest_json': True,
                        'ui_total_shards': 3, 'ui_shard_index': 3,
                        'browser_total_shards': 3, 'browser_shard_index': 3,}))

B('Linux Builder (Views dbg)', 'view_dbg', 'compile', 'chromeos_dbg')
F('view_dbg', chromeos().ChromiumOSFactory(
    slave_type='NASBuilder',
    target='Debug',
    options=['--compiler=goma',
             'app_unittests',
             'base_unittests',
             'browser_tests',
             'interactive_ui_tests',
             'ipc_tests',
             'googleurl_unittests',
             'media_unittests',
             'net_unittests',
             'printing_unittests',
             'remoting_unittests',
             'sync_unit_tests',
             'ui_tests',
             'unit_tests',
             'views_unittests',
             'gfx_unittests',
             'crypto_unittests',
             'cacheinvalidation_unittests',
             'jingle_unittests'],
    factory_properties={'gclient_env':
                            {'GYP_DEFINES':'toolkit_views=1 chromeos=1'},
                        'trigger': 'linux_views_dbg_trigger'}))

B('Linux Tests (Views dbg)(1)', 'view_dbg_tests_1', 'testers',
  'linux_views_dbg_trigger')
F('view_dbg_tests_1', chromeos().ChromiumOSFactory(
    slave_type='NASTester',
    target='Debug',
    tests=['base',
           'browser_tests',
           'cacheinvalidation',
           'crypto',
           'googleurl',
           'interactive_ui',
           'jingle',
           'media',
           'printing',
           'remoting',
           'ui',
           'views'],
    factory_properties={'generate_gtest_json': True,
                        'ui_total_shards': 3, 'ui_shard_index': 1,
                        'browser_total_shards': 3, 'browser_shard_index': 1,}))

B('Linux Tests (Views dbg)(2)', 'view_dbg_tests_2', 'testers',
  'linux_views_dbg_trigger')
F('view_dbg_tests_2', chromeos().ChromiumOSFactory(
    slave_type='NASTester',
    target='Debug',
    tests=['browser_tests', 'ui', 'unit',],
    factory_properties={'generate_gtest_json': True,
                        'ui_total_shards': 3, 'ui_shard_index': 2,
                        'browser_total_shards': 3, 'browser_shard_index': 2,}))

B('Linux Tests (Views dbg)(3)', 'view_dbg_tests_3', 'testers',
  'linux_views_dbg_trigger')
F('view_dbg_tests_3', chromeos().ChromiumOSFactory(
    slave_type='NASTester',
    target='Debug',
    tests=['browser_tests', 'net', 'ui',],
    factory_properties={'generate_gtest_json': True,
                        'ui_total_shards': 3, 'ui_shard_index': 3,
                        'browser_total_shards': 3, 'browser_shard_index': 3,}))

#
# Linux ChromiumOS Dbg Clang bot
#

B('Linux Clang (ChromiumOS dbg)',
    'dbg_linux_chromeos_clang', 'compile', 'chromeos_dbg')
F('dbg_linux_chromeos_clang', chromeos().ChromiumOSFactory(
    target='Debug',
    options=['--build-tool=make', '--compiler=clang'],
    tests=['base',
           'ui_base',
           'gfx',
           'unit',
           'crypto',
           'cacheinvalidation',
           'jingle'],
    factory_properties={
        'gclient_env': {
            'GYP_DEFINES':'clang=1 clang_use_chrome_plugins=1 ' + 
                          'chromeos=1 fastbuild=1 target_arch=ia32'
    }}))


def Update(config, active_master, c):
  return helper.Update(c)
