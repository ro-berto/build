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

def chromiumos(): return chromium_factory.ChromiumFactory('src/build', 'linux2')

defaults['category'] = '1linux'

S(name='chromium_local', branch='src', treeStableTimer=60)

T('chromiumos_rel_trigger')

# Tests that are single-machine shard-safe. For now we only use the sharding
# supervisor for long tests (more than 30 seconds) that are known to be stable.
sharded_tests = [
  'base_unittests',
  'browser_tests',
  'content_unittests',
  'media_unittests',
]

linux_options = [
    'aura_builder',
    'base_unittests',
    'browser_tests',
    'cacheinvalidation_unittests',
    'compositor_unittests',
    'content_unittests',
    'crypto_unittests',
    'dbus_unittests',
    'gfx_unittests',
    'gpu_unittests',
    'googleurl_unittests',
    'interactive_ui_tests',
    'ipc_tests',
    'jingle_unittests',
    'media_unittests',
    'net_unittests',
    'printing_unittests',
    #'remoting_unittests',
    #'safe_browsing_tests',
    'sql_unittests',
    'sync_unit_tests',
    'ui_tests',
    'unit_tests',
    'views_unittests',
]

linux_tests_1 = [
    'aura',
    'aura_shell',
    'base',
    'cacheinvalidation',
    'compositor',
    'crypto',
    'dbus',
    'gfx',
    'googleurl',
    'gpu',
    'ipc',
    'jingle',
    'media',
    'net',
    'printing',
    #'remoting',
    #'safe_browsing'
    'sql',
    'DISABLED_sync',
    'unit',
    'views',
]

linux_tests_2 = [ 'browser_tests' ]
linux_tests_3 = [ 'ui', 'interactive_ui' ]

B('Linux ChromiumOS Builder',
  factory='builder',
  gatekeeper='compile',
  builddir='chromium-rel-linux-chromeos',
  scheduler='chromium_local',
  notify_on_missing=True)
F('builder', chromiumos().ChromiumOSFactory(
    slave_type='NASBuilder',
    options=['--compiler=goma'] + linux_options,
    factory_properties={
        'archive_build': False,
        'trigger': 'chromiumos_rel_trigger',
        'extra_archive_paths': 'chrome/tools/build/chromeos',
        'gclient_env': {
            'GYP_DEFINES': ('chromeos=1'
                            ' ffmpeg_branding=ChromeOS proprietary_codecs=1'
                            ' component=shared_library')},
        'window_manager': False}))

B('Linux ChromiumOS Tests (1)',
  factory='tester_1',
  scheduler='chromiumos_rel_trigger',
  gatekeeper='tester',
  auto_reboot=True,
  notify_on_missing=True)
F('tester_1', chromiumos().ChromiumOSFactory(
    slave_type='NASTester',
    tests=['aura',
           'aura_shell',
           'base',
           'cacheinvalidation',
           'compositor',
           'crypto',
           'dbus',
           'gfx',
           'googleurl',
           'gpu',
           'ipc',
           'jingle',
           'media',
           'net',
           'printing',
           #'remoting',
           #'safe_browsing'
           'sql',
           'DISABLED_sync',
           'unit',
           'views',
           ],
    factory_properties={'sharded_tests': sharded_tests,
                        'generate_gtest_json': True,
                        'chromeos': 1}))


B('Linux ChromiumOS Tests (2)',
  factory='tester_2',
  scheduler='chromiumos_rel_trigger',
  gatekeeper='tester',
  auto_reboot=True,
  notify_on_missing=True)
F('tester_2', chromiumos().ChromiumOSFactory(
    slave_type='NASTester',
    tests=linux_tests_2 + linux_tests_3,
    factory_properties={'sharded_tests': sharded_tests,
                        'generate_gtest_json': True,
                        'chromeos': 1}))


B('Linux ChromiumOS (Clang dbg)',
  factory='clang',
  gatekeeper='compile|tester',
  builddir='chromium-dbg-linux-chromeos-clang',
  scheduler='chromium_local',
  notify_on_missing=True)
F('clang', chromiumos().ChromiumOSFactory(
    target='Debug',
    tests=[],
    options=['--compiler=clang', 'aura_builder'],
    factory_properties={
        'gclient_env': {
            'GYP_DEFINES': ('chromeos=1 target_arch=ia32'
                            ' clang=1 clang_use_chrome_plugins=1'
                            ' fastbuild=1'
                            ' ffmpeg_branding=ChromeOS proprietary_codecs=1'
                            ' component=shared_library'
                           )}}))
#
# Triggerable scheduler for the dbg builders
#
T('chromiumos_dbg_trigger')

B('Linux ChromiumOS Builder (dbg)', 'dbg', 'compile',
  'chromium_local', notify_on_missing=True)
F('dbg', chromiumos().ChromiumOSFactory(
    slave_type='NASBuilder',
    target='Debug',
    options=['--compiler=goma'] + linux_options,
    factory_properties={
      'gclient_env': { 'GYP_DEFINES' : 'chromeos=1 component=shared_library' },
      'trigger': 'chromiumos_dbg_trigger',
      'window_manager': False,
    }))

B('Linux ChromiumOS Tests (dbg)(1)', 'dbg_tests_1', 'tester',
  'chromiumos_dbg_trigger', auto_reboot=True, notify_on_missing=True)
F('dbg_tests_1', chromiumos().ChromiumOSFactory(
    slave_type='NASTester',
    target='Debug',
    tests=linux_tests_1,
    factory_properties={'sharded_tests': sharded_tests,
                        'generate_gtest_json': True,}))


B('Linux ChromiumOS Tests (dbg)(2)', 'dbg_tests_2', 'tester',
  'chromiumos_dbg_trigger', auto_reboot=True, notify_on_missing=True)
F('dbg_tests_2', chromiumos().ChromiumOSFactory(
    slave_type='NASTester',
    target='Debug',
    tests=linux_tests_2,
    factory_properties={'sharded_tests': sharded_tests,
                        'generate_gtest_json': True,}))


B('Linux ChromiumOS Tests (dbg)(3)', 'dbg_tests_3', 'tester',
  'chromiumos_dbg_trigger', auto_reboot=True, notify_on_missing=True)
F('dbg_tests_3', chromiumos().ChromiumOSFactory(
    slave_type='NASTester',
    target='Debug',
    tests=linux_tests_3,
    factory_properties={'sharded_tests': sharded_tests,
                        'generate_gtest_json': True,}))



def Update(config, active_master, c):
  return helper.Update(c)
