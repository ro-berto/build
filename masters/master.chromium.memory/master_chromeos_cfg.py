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

# CrOS ASan bots below.
defaults['category'] = '3chromeos asan'

#
# Main asan release scheduler for src/
#
S('chromeos_asan_rel', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the rel asan builder
#
T('chromeos_asan_rel_trigger')

chromeos_asan_archive = master_config.GetArchiveUrl('ChromiumMemory',
                                                    'Chromium OS ASAN Builder',
                                                    'Chromium_OS_ASAN_Builder',
                                                    'linux')
#
# CrOS ASAN Rel Builder
#
linux_aura_options = [
  'aura_builder',
  'base_unittests',
  'browser_tests',
  'cacheinvalidation_unittests',
  'compositor_unittests',
  'content_unittests',
  'crypto_unittests',
  'googleurl_unittests',
  'gpu_unittests',
  'interactive_ui_tests',
  'ipc_tests',
  'jingle_unittests',
  'net_unittests',
  'media_unittests',
  'printing_unittests',
  'remoting_unittests',
  'safe_browsing_tests',
  'sql_unittests',
  'ui_unittests',
]

# Please do not add release_extra_cflags=-g here until the debug info section
# produced by Clang on Linux is small enough.
fp_chromeos_asan = {
    'asan': True,
    'gclient_env': {
        'GYP_DEFINES': ('asan=1 '
                        'linux_use_tcmalloc=0 '
                        'chromeos=1 '),
        'GYP_GENERATORS': 'ninja' }}

B('Chromium OS ASAN Builder', 'chromeos_asan_rel', 'compile',
  'chromeos_asan_rel', notify_on_missing=True)
F('chromeos_asan_rel', linux().ChromiumASANFactory(
    slave_type='Builder',
    options=[
      '--build-tool=ninja',
      '--compiler=goma-clang',
    ] + linux_aura_options,
    factory_properties=dict(fp_chromeos_asan,
                            trigger='linux_asan_rel_trigger')))

#
# CrOS ASAN Rel testers
#

asan_tests_1 = [
  'aura',
  'aura_shell',
  'base',
  'browser_tests',
  'cacheinvalidation',
  'compositor',
  'crypto',
  'googleurl',
  'gpu',
  'jingle',
  'media',
  'printing',
  'remoting',
  'safe_browsing',
  'views',
]

asan_tests_2 = [
  'browser_tests',
  'net',
  'unit',
]

B('Chromium OS ASAN Tests (1)', 'chromeos_asan_rel_tests_1', 'testers',
  'chromeos_asan_rel_trigger', auto_reboot=True, notify_on_missing=True)
F('chromeos_asan_rel_tests_1', linux().ChromiumASANFactory(
    slave_type='Tester',
    build_url=chromeos_asan_archive,
    tests=asan_tests_1,
    factory_properties=dict(fp_chromeos_asan,
                            browser_total_shards='2',
                            browser_shard_index='1')))

B('Chromium OS ASAN Tests (2)', 'chromeos_asan_rel_tests_2', 'testers',
  'chromeos_asan_rel_trigger', auto_reboot=True, notify_on_missing=True)
F('chromeos_asan_rel_tests_2', linux().ChromiumASANFactory(
    slave_type='Tester',
    build_url=chromeos_asan_archive,
    tests=asan_tests_2,
    factory_properties=dict(fp_chromeos_asan,
                            browser_total_shards='2',
                            browser_shard_index='2')))

def Update(config, active_master, c):
  return helper.Update(c)
