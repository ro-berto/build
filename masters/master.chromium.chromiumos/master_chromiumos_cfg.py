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

################################################################################
## Debug
################################################################################

S(name='chromium_local', branch='src', treeStableTimer=60)


B('Linux ChromiumOS',
  factory='basic',
  gatekeeper='compile|tester',
  builddir='chromium-rel-linux-chromeos',
  scheduler='chromium_local',
  notify_on_missing=True)
F('basic', chromiumos().ChromiumOSFactory(
    tests=['aura',
           'aura_shell',
           'base',
           'browser_tests',
           'cacheinvalidation',
           'content',
           'compositor',
           'crypto',
           'dbus',
           'gfx',
           'googleurl',
           'interactive_ui',
           'ipc',
           'jingle',
           'media',
           'net',
           'printing',
           #'remoting',
           #'safe_browsing'
           'sql',
           'DISABLED_sync',
           'ui',
           'unit',
           'views',
           ],
    options=['--compiler=goma',
             'aura_builder',
             'base_unittests',
             'browser_tests',
             'cacheinvalidation_unittests',
             'compositor_unittests',
             'content_unittests',
             'crypto_unittests',
             'dbus_unittests',
             'gfx_unittests',
             #'gpu_unittests',
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
             ],
    factory_properties={
        'archive_build': False,
        'extra_archive_paths': 'chrome/tools/build/chromeos',
        'gclient_env': {
            'GYP_DEFINES': ('chromeos=1 target_arch=ia32'
                            ' ffmpeg_branding=ChromeOS proprietary_codecs=1')},
        'generate_gtest_json': True,
        'window_manager': False}))


B('Linux ChromiumOS GTK',
  factory='gtk',
  gatekeeper='compile|tester',
  builddir='chromium-rel-linux-chromeos-gtk',
  scheduler='chromium_local',
  notify_on_missing=True)
F('gtk', chromiumos().ChromiumOSFactory(
    tests=['base',
           'browser_tests',
           'cacheinvalidation',
           'content',
           'compositor',
           'crypto',
           'dbus',
           'gfx',
           'googleurl',
           'interactive_ui',
           'ipc',
           'jingle',
           'media',
           'net',
           'printing',
           #'remoting',
           #'safe_browsing'
           'sql',
           'DISABLED_sync',
           'ui',
           'unit',
           'views',
           ],
    options=['--compiler=goma',
             'base_unittests',
             'browser_tests',
             'cacheinvalidation_unittests',
             'chromeos_builder',
             'compositor_unittests',
             'content_unittests',
             'crypto_unittests',
             'dbus_unittests',
             'gfx_unittests',
             #'gpu_unittests',
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
             ],
    factory_properties={
        'archive_build': False,
        'extra_archive_paths': 'chrome/tools/build/chromeos',
        'gclient_env': {
            'GYP_DEFINES': ('chromeos=1 chromeos_gtk=1 target_arch=ia32'
                            ' ffmpeg_branding=ChromeOS proprietary_codecs=1')},
        'generate_gtest_json': True,
        'window_manager': True}))


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
    options=['--compiler=goma',
             'aura_builder',
             'base_unittests',
             'browser_tests',
             'cacheinvalidation_unittests',
             'compositor_unittests',
             'content_unittests',
             'crypto_unittests',
             'dbus',
             'gfx_unittests',
             'googleurl_unittests',
             'interactive_ui_tests',
             'ipc_tests',
             'jingle_unittests',
             'media_unittests',
             'net_unittests',
             'printing_unittests',
             #'remoting_unittests',
             'sync_unit_tests',
             'sql_unittests',
             'ui_tests',
             'unit_tests',
             'views_unittests',
             ],
    factory_properties={
      'gclient_env': { 'GYP_DEFINES' : 'chromeos=1' },
      'trigger': 'chromiumos_dbg_trigger',
      'window_manager': False,
    }))

B('Linux ChromiumOS Tests (dbg)', 'dbg_tests_1', 'tester',
  'chromiumos_dbg_trigger', auto_reboot=True, notify_on_missing=True)
F('dbg_tests_1', chromiumos().ChromiumOSFactory(
    slave_type='NASTester',
    target='Debug',
    tests=['aura',
           'aura_shell',
           'DISABLED_base',
           'DISABLED_browser_tests',
           'cacheinvalidation',
           'compositor',
           'content',
           'crypto',
           'gfx',
           'googleurl',
           'DISABLED_interactive_ui',
           'ipc',
           'jingle',
           'media',
           'net',
           'printing',
           #'DISABLED_remoting',
           'DISABLED_sql',
           'DISABLED_sync',
           'DISABLED_ui'
           'unit',
           'views',
           ],
    factory_properties={'generate_gtest_json': True,}))



def Update(config, active_master, c):
  return helper.Update(c)
