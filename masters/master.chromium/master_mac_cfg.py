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

def mac(): return chromium_factory.ChromiumFactory('src/build', 'darwin')


################################################################################
## Release
################################################################################

defaults['category'] = '3mac'

# Archive location
rel_archive = master_config.GetArchiveUrl('Chromium', 'Mac Builder',
                                          'cr-mac-rel', 'mac')

#
# Main debug scheduler for src/
#
S('mac_rel', branch='src', treeStableTimer=60)

#
# Dependent scheduler for the dbg builder
#
D('mac_rel_dep', 'mac_rel')

#
# Mac Rel Builder
#
B('Mac Builder', 'rel', 'compile', 'mac_rel', builddir='cr-mac-rel')
F('rel', mac().ChromiumFactory(
    'chromium-mac-rel',
    slave_type='Builder',
    options=['--', '-target', 'chromium_builder_tests']))

#
# Mac Rel testers
#
B('Mac10.5 Tests', 'rel_unit', 'testers', 'mac_rel_dep')
F('rel_unit', mac().ChromiumFactory(
  'chromium-mac-rel',
  slave_type='Tester',
  build_url=rel_archive,
  tests=['unit', 'ui', 'media', 'printing', 'remoting', 'gpu', 'browser_tests',
         'googleurl', 'nacl_ui', 'nacl_sandbox', 'base', 'net'],
  factory_properties={'generate_gtest_json': True})
)

B('Mac10.6 Tests', 'rel_unit', 'testers', 'mac_rel_dep')

################################################################################
## Debug
################################################################################

dbg_archive = master_config.GetArchiveUrl('Chromium', 'Mac Builder (dbg)',
                                          'cr-mac-dbg', 'mac')

#
# Main debug scheduler for src/
#
S('mac_dbg', branch='src', treeStableTimer=60)

#
# Dependent scheduler for the dbg builder
#
D('mac_dbg_dep', 'mac_dbg')

#
# Mac Dbg Builder
#
B('Mac Builder (dbg)', 'dbg', 'compile', 'mac_dbg', builddir='cr-mac-dbg')
F('dbg', mac().ChromiumFactory(
    'chromium-mac-dbg',
    target='Debug',
    slave_type='Builder',
    options=['--', '-target', 'chromium_builder_tests']))

#
# Mac Dbg Unit testers
#

B('Mac 10.5 Tests (dbg)(1)', 'dbg_unit_1', 'testers', 'mac_dbg_dep')
F('dbg_unit_1', mac().ChromiumFactory(
  'chromium-mac-dbg',
  slave_type='Tester',
  target='Debug',
  build_url=dbg_archive,
  tests=['check_deps', 'media', 'printing', 'remoting', 'unit', 'googleurl',
         'nacl_ui', 'gpu', 'interactive_ui', 'nacl_sandbox', 'base'],
  factory_properties={'generate_gtest_json': True}))

B('Mac 10.5 Tests (dbg)(2)', 'dbg_unit_2', 'testers', 'mac_dbg_dep')
F('dbg_unit_2', mac().ChromiumFactory(
  'chromium-mac-dbg',
  slave_type='Tester',
  target='Debug',
  build_url=dbg_archive,
  tests=['ui', 'net'],
  factory_properties={'generate_gtest_json': True}))

B('Mac 10.5 Tests (dbg)(3)', 'dbg_unit_3', 'testers', 'mac_dbg_dep')
F('dbg_unit_3', mac().ChromiumFactory(
  'chromium-mac-dbg',
  slave_type='Tester',
  target='Debug',
  build_url=dbg_archive,
  tests=['browser_tests'],
  factory_properties={'generate_gtest_json': True}))

B('Mac 10.6 Tests (dbg)(1)', 'dbg_unit_1', 'testers', 'mac_dbg_dep')
B('Mac 10.6 Tests (dbg)(2)', 'dbg_unit_2', 'testers', 'mac_dbg_dep')
B('Mac 10.6 Tests (dbg)(3)', 'dbg_unit_3', 'testers', 'mac_dbg_dep')

def Update(config, active_master, c):
  return helper.Update(c)
