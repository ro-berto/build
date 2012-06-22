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

def linux(): return chromium_factory.ChromiumFactory('src/build', 'linux2')

defaults['category'] = '1linux asan'

#
# Main asan release scheduler for src/
#
S('linux_asan_rel', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the rel asan builder
#
T('linux_asan_rel_trigger')

asan_archive = master_config.GetArchiveUrl('ChromiumMemory', 'ASAN Builder',
                                           'ASAN_Builder', 'linux')
#
# Linux ASAN Rel Builder
#
B('ASAN Builder', 'asan_rel', 'compile', 'linux_asan_rel',
  notify_on_missing=True)
# Please do not add release_extra_cflags=-g here until the debug info section
# produced by Clang on Linux is small enough.
F('asan_rel', linux().ChromiumASANFactory(
    slave_type='Builder',
    options=[
      '--compiler=goma-clang',
      'base_unittests',
      'browser_tests',
      'cacheinvalidation_unittests',
      'content_unittests',
      'crypto_unittests',
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
    ],
    factory_properties={
           'gclient_env': {'GYP_DEFINES':
                              ('asan=1 '
                               'linux_use_tcmalloc=0 ')},
            'trigger': 'linux_asan_rel_trigger' }))

#
# Linux ASAN Rel testers
#
B('ASAN Tests (1)', 'asan_rel_tests_1', 'testers', 'linux_asan_rel_trigger',
  auto_reboot=True, notify_on_missing=True)
F('asan_rel_tests_1', linux().ChromiumASANFactory(
    slave_type='Tester',
       build_url=asan_archive,
    tests=[
      'base',
      'cacheinvalidation',
      'crypto',
      'gpu',
      'jingle',
      'net',
      'safe_browsing',
      'unit',
    ],
    factory_properties={'asan': True}))

B('ASAN Tests (2)', 'asan_rel_tests_2', 'testers', 'linux_asan_rel_trigger',
  auto_reboot=True, notify_on_missing=True)
F('asan_rel_tests_2', linux().ChromiumASANFactory(
    slave_type='Tester',
       build_url=asan_archive,
    tests=[
      'browser_tests',
      'googleurl',
      'media',
      'printing',
      'remoting',
    ],
    factory_properties={'asan': True}))

def Update(config, active_master, c):
  return helper.Update(c)
