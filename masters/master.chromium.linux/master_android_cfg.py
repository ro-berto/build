# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.process.properties import WithProperties
from buildbot.schedulers.basic import SingleBranchScheduler

from master import master_config
from master import master_utils
from master.factory import remote_run_factory

import master_site_config
ActiveMaster = master_site_config.ChromiumLinux

revision_getter = master_utils.ConditionalProperty(
    lambda build: build.getProperty('revision'),
    WithProperties('%(revision)s'),
    'master')

def m_remote_run_chromium_src(recipe, **kwargs):
  kwargs.setdefault('revision', revision_getter)
  return remote_run_factory.RemoteRunFactory(
      active_master=ActiveMaster,
      repository='https://chromium.googlesource.com/chromium/src.git',
      recipe=recipe,
      factory_properties={'path_config': 'kitchen'},
      use_gitiles=True,
      **kwargs)

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler
T = helper.Triggerable

defaults['category'] = '5android'

android_dbg_archive = master_config.GetGSUtilUrl(
    'chromium-android', 'android_main_dbg')

android_rel_archive = master_config.GetGSUtilUrl(
    'chromium-android', 'android_main_rel')

#
# Main release scheduler for src/
#
S('android', branch='master', treeStableTimer=60)

#
# Triggerable scheduler for the builder
#
T('android_trigger_dbg')
T('android_trigger_rel')

#
# Android Builder
#
B('Android Arm64 Builder (dbg)', 'f_android_arm64_dbg', 'android', 'android',
  auto_reboot=False, notify_on_missing=True)
F('f_android_arm64_dbg', m_remote_run_chromium_src('chromium'))

B('Android Builder (dbg)', 'f_android_dbg', 'android', 'android',
  auto_reboot=False, notify_on_missing=True)
F('f_android_dbg', m_remote_run_chromium_src('chromium'))

B('Android Tests (dbg)', 'f_android_dbg_tests', 'android',
  'android_trigger_dbg', notify_on_missing=True)
F('f_android_dbg_tests', m_remote_run_chromium_src('chromium'))

B('Android Builder', 'f_android_rel', 'android', 'android',
  notify_on_missing=True)
F('f_android_rel', m_remote_run_chromium_src('chromium'))

B('Android Tests', 'f_android_rel_tests', 'android', 'android_trigger_rel',
  notify_on_missing=True)
F('f_android_rel_tests', m_remote_run_chromium_src('chromium'))

B('Android Clang Builder (dbg)', 'f_android_clang_dbg', 'android', 'android',
  notify_on_missing=True)
F('f_android_clang_dbg', m_remote_run_chromium_src('chromium'))

def Update(_config_arg, _active_master, c):
  helper.Update(c)

  specs = [
    {'name': 'Cast Android (dbg)'},
  ]

  c['schedulers'].extend([
      SingleBranchScheduler(name='android_gn',
                            branch='master',
                            treeStableTimer=60,
                            builderNames=[s['name'] for s in specs]),
  ])
  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_remote_run_chromium_src('chromium'),
        'notify_on_missing': True,
        'category': '5android',
      } for spec in specs
  ])
