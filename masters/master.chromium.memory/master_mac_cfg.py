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

def mac(): return chromium_factory.ChromiumFactory('src/build', 'darwin')

defaults['category'] = '2mac asan'

#
# Main asan release scheduler for src/
#
S('mac_asan_rel', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the rel asan builder
#
T('mac_asan_rel_trigger')

mac_asan_options = [
  'base_unittests',
  'browser_tests',
  'cacheinvalidation_unittests',
  'content_unittests',
  'crypto_unittests',
  'googleurl_unittests',
  'interactive_ui_tests',
  'ipc_tests',
  'jingle_unittests',
  'media_unittests',
  'printing_unittests',
  'remoting_unittests',
  'sql_unittests',
  'ui_unittests',
]

mac_asan_tests_1 = [
  'base',
  'browser_tests',
  'cacheinvalidation',
  'content',
  'crypto',
  'gfx',
  'googleurl',
  'jingle',
  'media',
  'printing',
  'remoting',
  'unit_ipc',
  'unit_sql',
]

mac_asan_tests_2 = [
  'browser_tests',
  'interactive_ui',
]

mac_asan_archive = master_config.GetArchiveUrl(
    'ChromiumMemory',
    'Mac ASAN Builder',
    'chromium-rel-mac-asan-builder',
    'mac')

#
# Mac ASAN Rel Builder
#
B('Mac ASAN Builder', 'mac_asan_rel', 'compile', 'mac_asan_rel',
  notify_on_missing=True)
F('mac_asan_rel', mac().ChromiumASANFactory(
    target='Release',
    slave_type='Builder',
    options=[
        '--build-tool=ninja',
        '--compiler=goma-clang',
        '--disable-aslr'
    ] + mac_asan_options,
    factory_properties={
      'asan': True,
      'package_dsym_files': True,
      'trigger': 'mac_asan_rel_trigger',
      'gclient_env': {
          'GYP_DEFINES': 'asan=1 release_extra_cflags=-g',
          'GYP_GENERATORS': 'ninja' }}
))

#
# Mac ASAN Rel testers
#
B('Mac ASAN Tests (1)', 'mac_asan_rel_tests_1', 'testers',
  'mac_asan_rel_trigger', auto_reboot=True, notify_on_missing=True)
F('mac_asan_rel_tests_1', mac().ChromiumASANFactory(
    slave_type='Tester',
    build_url=mac_asan_archive,
    tests=mac_asan_tests_1,
    factory_properties={
      'asan': True,
      'browser_total_shards': '2',
      'browser_shard_index': '1',
    }))


B('Mac ASAN Tests (2)', 'mac_asan_rel_tests_2', 'testers',
  'mac_asan_rel_trigger', auto_reboot=True, notify_on_missing=True)
F('mac_asan_rel_tests_2', mac().ChromiumASANFactory(
    slave_type='Tester',
    build_url=mac_asan_archive,
    tests=mac_asan_tests_2,
    factory_properties={
      'asan': True,
      'browser_total_shards': '2',
      'browser_shard_index': '2',
    }))

def Update(config, active_master, c):
  return helper.Update(c)
