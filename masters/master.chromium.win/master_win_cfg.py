# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Triggerable
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import remote_run_factory

import master_site_config
ActiveMaster = master_site_config.ChromiumWin


def m_remote_run(recipe, **kwargs):
  return remote_run_factory.RemoteRunFactory(
      active_master=ActiveMaster,
      repository='https://chromium.googlesource.com/chromium/tools/build.git',
      recipe=recipe,
      factory_properties={'path_config': 'kitchen'},
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
      ]),
  ])
  specs = [
    {'name': 'Win Builder'},
    {'name': 'Win7 (32) Tests'},
    {'name': 'Win7 Tests (1)'},
    {'name': 'Win x64 Builder'},
    {'name': 'Win 7 Tests x64 (1)'},
    {'name': 'Win x64 Builder (dbg)'},
    {'name': 'Win10 Tests x64'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_remote_run('chromium'),
        'notify_on_missing': True,
        'category': '2windows',
      } for spec in specs
  ])
