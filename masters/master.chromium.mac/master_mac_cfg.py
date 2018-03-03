# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.process.properties import WithProperties
from buildbot.scheduler import Triggerable
from buildbot.schedulers.basic import SingleBranchScheduler

from master import master_utils
from master.factory import remote_run_factory

import master_site_config
ActiveMaster = master_site_config.ChromiumMac


def m_remote_run(recipe, **kwargs):
  return remote_run_factory.RemoteRunFactory(
      active_master=ActiveMaster,
      repository='https://chromium.googlesource.com/chromium/tools/build.git',
      recipe=recipe,
      factory_properties={'path_config': 'kitchen'},
      max_time=7200, # 2 hours
      **kwargs)


def Update(config, active_master, c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='mac_src',
                            branch='master',
                            treeStableTimer=60,
                            builderNames=[
          'Mac Builder',
          'Mac Builder (dbg)',
      ]),
  ])
  specs = [
    {'name': 'Mac Builder'},
    {'name': 'Mac10.13 Tests'},
    {'name': 'Mac10.10 Tests'},
    {'name': 'Mac10.11 Tests'},
    {'name': 'Mac10.12 Tests'},
    {'name': 'Mac Builder (dbg)'},
    {'name': 'Mac10.13 Tests (dbg)'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_remote_run('chromium'),
        'notify_on_missing': True,
        'category': '3mac',
      } for spec in specs
  ])
