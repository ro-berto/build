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

defaults['category'] = '5chromiumos'

################################################################################
## Debug
################################################################################

#
# Main debug scheduler for src/
#
S('chromiumos_dbg', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the aura builders
#
T('chromiumos_aura_dbg_trigger')

B('Linux ChromiumOS Builder (dbg)', 'aura_dbg', 'compile',
  'chromiumos_dbg', notify_on_missing=True)
F('aura_dbg', chromiumos().ChromiumOSFactory(
    slave_type='NASBuilder',
    target='Debug',
    options=['--compiler=goma',
             'aura_builder',
             'base_unittests',
             'cacheinvalidation_unittests',
             'crypto_unittests',
             'googleurl_unittests',
             'jingle_unittests',
             'media_unittests',
             'printing_unittests',
             'views_unittests',
             'compositor_unittests',
             'ipc_tests',
             'sync_unit_tests',
             'sql_unittests',
             'gfx_unittests',
             'content_unittests',
             'browser_tests',
             'ui_tests',
             'interactive_ui_tests',
             'net_unittests',
             #'remoting_unittests',
             'unit_tests',
             ],
    factory_properties={
      'gclient_env': { 'GYP_DEFINES' : 'chromeos=1' },
      'trigger': 'chromiumos_aura_dbg_trigger',
      'window_manager': False,
    }))

B('Linux ChromiumOS Tests (dbg)', 'aura_dbg_tests_1', 'testers',
  'chromiumos_aura_dbg_trigger', auto_reboot=True, notify_on_missing=True)
F('aura_dbg_tests_1', chromiumos().ChromiumOSFactory(
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
