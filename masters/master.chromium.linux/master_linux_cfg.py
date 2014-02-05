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
  return chromium_factory.ChromiumFactory('src/out', 'linux2')
def linux_tester():
  return chromium_factory.ChromiumFactory(
      'src/out', 'linux2', nohooks_on_update=True)

# Tests that are single-machine shard-safe.
sharded_tests = [
  'aura_unittests',
  'base_unittests',
  'browser_tests',
  'cacheinvalidation_unittests',
  'cast_unittests',
  'cc_unittests',
  'chromedriver_tests',
  'chromedriver_unittests',
  'components_unittests',
  'content_browsertests',
  'content_unittests',
  'crypto_unittests',
  'device_unittests',
  'events_unittests',
  'gpu_unittests',
  'jingle_unittests',
  'media_unittests',
  'net_unittests',
  'ppapi_unittests',
  'printing_unittests',
  'remoting_unittests',
  'sync_integration_tests',
  'sync_unit_tests',
  'ui_unittests',
  'unit_tests',
  'views_unittests',
  'webkit_compositor_bindings_unittests',
]

# These are the common targets to most of the builders
linux_all_test_targets = [
  'base_unittests',
  'browser_tests',
  'cacheinvalidation_unittests',
  'cast_unittests',
  'cc_unittests',
  'chrome',
  'chromedriver_unittests',
  'components_unittests',
  'content_browsertests',
  'content_unittests',
  'crypto_unittests',
  'dbus_unittests',
  'device_unittests',
  'google_apis_unittests',
  'gpu_unittests',
  'interactive_ui_tests',
  'ipc_tests',
  'jingle_unittests',
  'media_unittests',
  'net_unittests',
  'ppapi_unittests',
  'printing_unittests',
  'remoting_unittests',
  'sandbox_linux_unittests',
  'sql_unittests',
  'sync_unit_tests',
  'ui_unittests',
  'unit_tests',
  'url_unittests',
  'webkit_compositor_bindings_unittests',
]

linux_gtk_test_targets = [
  'app_list_unittests',
  'aura_builder',
  'compositor_unittests',
]

goma_ninja_options = [
    '--build-tool=ninja', '--compiler=goma', '--']
goma_clang_ninja_options = [
    '--build-tool=ninja', '--compiler=goma-clang', '--']

################################################################################
## Release
################################################################################

defaults['category'] = '4linux'

rel_archive = master_config.GetArchiveUrl(
    'ChromiumLinux', 'Linux Builder',
    'Linux_Builder', 'linux')

rel_gtk_archive = master_config.GetArchiveUrl(
    'ChromiumLinux', 'Linux GTK Builder',
    'Linux_GTK_Builder', 'linux')

#
# Main release scheduler for src/
#
S('linux_rel', branch='src', treeStableTimer=60)

#
# Triggerable schedulers for the rel builders
#
T('linux_rel_trigger')
T('linux_rel_gtk_trigger')

#
# Linux Rel Builder
#
B('Linux Builder', 'rel', 'compile', 'linux_rel',
  auto_reboot=False, notify_on_missing=True)
F('rel', linux().ChromiumFactory(
    slave_type='Builder',
    options=goma_ninja_options + linux_all_test_targets +
            ['sync_integration_tests', 'chromium_swarm_tests'],
    tests=['check_deps'],
    factory_properties={
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
        },
        'trigger': 'linux_rel_trigger',
    }))

#
# Linux Rel testers
#
B('Linux Tests',
  'rel_unit',
  'testers',
  'linux_rel_trigger',
  notify_on_missing=True)
F('rel_unit', linux_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=[
      'base_unittests',
      'browser_tests',
      'cacheinvalidation_unittests',
      'cast',
      'cc_unittests',
      'chromedriver_unittests',
      'components_unittests',
      'content_browsertests',
      'content_unittests',
      'crypto_unittests',
      'dbus',
      'device_unittests',
      'google_apis_unittests',
      'googleurl',
      'gpu',
      'interactive_ui_tests',
      'ipc_tests',
      'jingle',
      'media',
      'net',
      'ppapi_unittests',
      'printing',
      'remoting',
      'sandbox_linux_unittests',
      'telemetry_perf_unittests',
      'telemetry_unittests',
      'ui_unittests',
      'unit_sql',
      'unit_sync',
      'unit_unit',
      'webkit_compositor_bindings_unittests',
    ],
    factory_properties={'sharded_tests': sharded_tests,
                        'generate_gtest_json': True}))

B('Linux Sync',
  'rel_sync',
  'testers',
  'linux_rel_trigger',
  notify_on_missing=True)
F('rel_sync', linux_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=['sync_integration'],
    factory_properties={
      'generate_gtest_json': True,
      'sharded_tests': sharded_tests,
    }))

#
# Linux GTK bot
#
B('Linux GTK Builder', 'rel_gtk', 'compile', 'linux_rel',
  auto_reboot=False, notify_on_missing=True)
F('rel_gtk', linux().ChromiumFactory(
    slave_type='Builder',
    options=goma_ninja_options + linux_all_test_targets +
            linux_gtk_test_targets +
            ['sync_integration_tests', 'chromium_swarm_tests'],
    tests=['check_deps'],
    factory_properties={
      'gclient_env': {
          'GYP_DEFINES': 'use_aura=0',
          'GYP_GENERATORS': 'ninja',
      },
      'trigger': 'linux_rel_gtk_trigger',
    }))

#
# Linux GTK tests
#
B('Linux GTK Tests',
  'rel_gtk_unit',
  'testers',
  'linux_rel_gtk_trigger',
  notify_on_missing=True)
F('rel_gtk_unit', linux_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_gtk_archive,
    tests=[
      'app_list_unittests',
      'aura',
      'base_unittests',
      'browser_tests',
      'cacheinvalidation_unittests',
      'cast',
      'cc_unittests',
      'chromedriver_unittests',
      'components_unittests',
      'compositor',
      'content_browsertests',
      'content_unittests',
      'crypto_unittests',
      'dbus',
      'device_unittests',
      'events',
      'google_apis_unittests',
      'googleurl',
      'gpu',
      'interactive_ui_tests',
      'ipc_tests',
      'jingle',
      'media',
      'net',
      'ppapi_unittests',
      'printing',
      'remoting',
      'sandbox_linux_unittests',
      'ui_unittests',
      'unit_sql',
      'unit_sync',
      'unit_unit',
      'views',
      'webkit_compositor_bindings_unittests',
    ],
    factory_properties={'sharded_tests': sharded_tests,
                        'generate_gtest_json': True}))


################################################################################
## Debug
################################################################################

#
# Main debug scheduler for src/
#
S('linux_dbg', branch='src', treeStableTimer=60)

dbg_archive = master_config.GetArchiveUrl(
    'ChromiumLinux',
    'Linux Builder (dbg)',
    'Linux_Builder__dbg_', 'linux')
dbg_32_archive = master_config.GetArchiveUrl(
    'ChromiumLinux',
    'Linux Builder (dbg)(32)',
    'Linux_Builder__dbg__32_', 'linux')

#
# Triggerable scheduler for the dbg builders
#
T('linux_dbg_trigger')
T('linux_dbg_32_trigger')

B('Linux Builder (dbg)(32)', 'dbg_32', 'compile', 'linux_dbg',
  auto_reboot=False, notify_on_missing=True)
F('dbg_32', linux().ChromiumFactory(
    slave_type='Builder',
    target='Debug',
    options=goma_ninja_options + linux_all_test_targets,
    factory_properties={
        'gclient_env': {
            'GYP_DEFINES':'target_arch=ia32',
            'GYP_GENERATORS':'ninja',
        },
        'trigger': 'linux_dbg_32_trigger',
    }))

#
# Linux Dbg Unit testers
#

B('Linux Tests (dbg)(1)(32)',
    factory='dbg_unit_32_1',
    gatekeeper='testers',
    scheduler='linux_dbg_32_trigger',
    notify_on_missing=True)
F('dbg_unit_32_1', linux_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=dbg_32_archive,
    target='Debug',
    tests=[
      'browser_tests',
      'content_browsertests',
      'net',
    ],
    factory_properties={'sharded_tests': sharded_tests,
                        'generate_gtest_json': True}))

B('Linux Tests (dbg)(2)(32)',
    factory='dbg_unit_32_2',
    gatekeeper='testers',
    scheduler='linux_dbg_32_trigger',
    notify_on_missing=True)
F('dbg_unit_32_2', linux_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=dbg_32_archive,
    target='Debug',
    tests=[
      'base_unittests',
      'cacheinvalidation_unittests',
      'cast',
      'cc_unittests',
      'chromedriver_unittests',
      'components_unittests',
      'content_unittests',
      'crypto_unittests',
      'dbus',
      'device_unittests',
      'googleurl',
      'gpu',
      'interactive_ui_tests',
      'ipc_tests',
      'jingle',
      'media',
      'nacl_integration',
      'ppapi_unittests',
      'printing',
      'remoting',
      'sandbox_linux_unittests',
      'ui_unittests',
      'unit_sql',
      'unit_sync',
      'unit_unit',
      'webkit_compositor_bindings_unittests',
    ],
    factory_properties={'sharded_tests': sharded_tests,
                        'generate_gtest_json': True}))

B('Linux Builder (dbg)', 'dbg', 'compile', 'linux_dbg',
  auto_reboot=False, notify_on_missing=True)
F('dbg', linux().ChromiumFactory(
    slave_type='Builder',
    target='Debug',
    options=goma_ninja_options + linux_all_test_targets,
    factory_properties={
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
        },
        'trigger': 'linux_dbg_trigger',
    }))

B('Linux Tests (dbg)(1)',
    factory='dbg_unit_1',
    gatekeeper='testers',
    scheduler='linux_dbg_trigger',
    notify_on_missing=True)
F('dbg_unit_1', linux_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=dbg_archive,
    target='Debug',
    tests=[
      'browser_tests',
      'content_browsertests',
      'net',
    ],
    factory_properties={'sharded_tests': sharded_tests,
                        'generate_gtest_json': True}))

B('Linux Tests (dbg)(2)',
    factory='dbg_unit_2',
    gatekeeper='testers',
    scheduler='linux_dbg_trigger',
    notify_on_missing=True)
F('dbg_unit_2', linux_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=dbg_archive,
    target='Debug',
    tests=[
      'base_unittests',
      'cacheinvalidation_unittests',
      'cast',
      'cc_unittests',
      'chromedriver_unittests',
      'components_unittests',
      'content_unittests',
      'crypto_unittests',
      'dbus',
      'device_unittests',
      'google_apis_unittests',
      'googleurl',
      'gpu',
      'interactive_ui_tests',
      'ipc_tests',
      'jingle',
      'media',
      'nacl_integration',
      'ppapi_unittests',
      'printing',
      'remoting',
      'sandbox_linux_unittests',
      'ui_unittests',
      'unit_sql',
      'unit_sync',
      'unit_unit',
      'webkit_compositor_bindings_unittests',
    ],
    factory_properties={'sharded_tests': sharded_tests,
                        'generate_gtest_json': True}))

#
# Linux Dbg Clang bot
#
B('Linux Clang (dbg)',
    factory='dbg_linux_clang',
    gatekeeper='compile|testers',
    scheduler='linux_dbg',
    notify_on_missing=True)
F('dbg_linux_clang', linux().ChromiumFactory(
    target='Debug',
    options=goma_clang_ninja_options,
    tests=[
      'base_unittests',
      'components_unittests',
      'content_unittests',
      'crypto_unittests',
      'device_unittests',
      'google_apis_unittests',
      'ipc_tests',
      'sandbox_linux_unittests',
      'ui_unittests',
      'unit_sql',
      'unit_sync',
      'unit_unit',
    ],
    factory_properties={
      'gclient_env': {
        'GYP_GENERATORS':'ninja',
        'GYP_DEFINES':
          'clang=1 clang_use_chrome_plugins=1 fastbuild=1 '
            'test_isolation_mode=noop',
    }}))

def Update(_config, _active_master, c):
  return helper.Update(c)
