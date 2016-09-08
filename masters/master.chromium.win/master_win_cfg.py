# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.process.properties import WithProperties
from buildbot.scheduler import Triggerable
from buildbot.schedulers.basic import SingleBranchScheduler

from master import master_utils
from master.factory import remote_run_factory

import master_site_config
ActiveMaster = master_site_config.ChromiumWin


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


def Update(config, active_master, c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='win_src',
                            branch='master',
                            treeStableTimer=60,
                            builderNames=[
          'Win Builder',
          'Win x64 Builder',
          'Win x64 Builder (dbg)',
          'Win Builder (dbg)',
          'WinClang64 (dbg)',
      ]),
  ])
  specs = [
    {'name': 'Win Builder'},
    {'name': 'Win7 (32) Tests'},
    {'name': 'Win7 Tests (1)'},
    {'name': 'Win x64 Builder'},
    {'name': 'Win 7 Tests x64 (1)'},
    {'name': 'Win x64 Builder (dbg)'},
    {'name': 'Win Builder (dbg)'},
    {'name': 'Win7 Tests (dbg)(1)'},
    {'name': 'WinClang64 (dbg)'},
    {'name': 'Win10 Tests x64'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_remote_run_chromium_src('chromium'),
        'notify_on_missing': True,
        'category': '2windows',
      } for spec in specs
  ])
