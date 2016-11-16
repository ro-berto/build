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
    {'name': 'Mac10.9 Tests'},
    {'name': 'Mac10.10 Tests'},
    {'name': 'Mac10.11 Tests'},
    {'name': 'Mac Builder (dbg)'},
    {'name': 'Mac10.9 Tests (dbg)'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_remote_run_chromium_src('chromium'),
        'notify_on_missing': True,
        'category': '3mac',
      } for spec in specs
  ])
