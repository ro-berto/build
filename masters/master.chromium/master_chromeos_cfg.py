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
T = helper.Triggerable

def chromeos(): return chromium_factory.ChromiumFactory('src/build', 'linux2')


################################################################################
## Release
################################################################################

defaults['category'] = '8chromiumos'

#
# Main debug scheduler for src/
#
S('chromeos_rel', branch='src', treeStableTimer=60)

#
# ChromeOS Rel Builder
#
B('Linux Builder (ChromiumOS)', 'rel', 'compile', 'chromeos_rel')
F('rel', chromeos().ChromiumOSFactory(
    tests=['unit', 'base', 'net', 'googleurl', 'media', 'ui', 'printing',
           'remoting', 'browser_tests', 'interactive_ui', 'views', 'crypto'],
    options=['chromeos_builder'],
    factory_properties={
        'archive_build': True,
        'extra_archive_paths': 'chrome/tools/build/chromeos',
        'gclient_env': { 'GYP_DEFINES':'chromeos=1'},
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
        'gclient_env': { 'GYP_DEFINES':'chromeos=1'},
        'trigger': 'linux_cros_dbg_trigger'}))

B('Linux Tester (ChromiumOS dbg)', 'cros_dbg_tests', 'testers',
  'linux_cros_dbg_trigger')
F('cros_dbg_tests', chromeos().ChromiumOSFactory(
    slave_type='NASTester',
    target='Debug',
    tests=['unit', 'base', 'net', 'googleurl', 'media', 'ui', 'printing',
           'remoting', 'browser_tests', 'interactive_ui', 'views', 'crypto'],
    factory_properties={'generate_gtest_json': True}))

B('Linux Builder (Views dbg)', 'view_dbg', 'compile', 'chromeos_dbg')
F('view_dbg', chromeos().ChromiumOSFactory(
    slave_type='NASBuilder',
    target='Debug',
    options=['--compiler=goma', 'app_unittests', 'base_unittests',
             'browser_tests', 'interactive_ui_tests', 'ipc_tests',
             'googleurl_unittests', 'media_unittests', 'net_unittests',
             'printing_unittests', 'remoting_unittests', 'sync_unit_tests',
             'ui_tests', 'unit_tests', 'views_unittests', 'gfx_unittests',
             'crypto_unittests'],
    factory_properties={'gclient_env': { 'GYP_DEFINES':'toolkit_views=1'},
                        'trigger': 'linux_views_dbg_trigger'}))

B('Linux Tester (Views dbg)', 'view_dbg_tests', 'testers',
  'linux_views_dbg_trigger')
F('view_dbg_tests', chromeos().ChromiumOSFactory(
    slave_type='NASTester',
    target='Debug',
    tests=['unit', 'base', 'net', 'googleurl', 'media', 'ui', 'printing',
           'remoting', 'browser_tests', 'interactive_ui', 'views', 'crypto'],
    factory_properties={'generate_gtest_json': True}))


def Update(config, active_master, c):
  return helper.Update(c)
