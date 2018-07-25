# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.changes.filter import ChangeFilter
from buildbot.process.properties import WithProperties
from buildbot.schedulers.basic import SingleBranchScheduler

from master import master_utils
from master.factory import remote_run_factory

import master_site_config
ActiveMaster = master_site_config.ChromiumWebRTC


def m_remote_run(recipe, **kwargs):
  return remote_run_factory.RemoteRunFactory(
      active_master=ActiveMaster,
      repository='https://chromium.googlesource.com/chromium/tools/build.git',
      recipe=recipe,
      factory_properties={'path_config': 'kitchen'},
      **kwargs)


def Update(c):
  c['schedulers'].append(
      SingleBranchScheduler(name='chromium_scheduler',
                            change_filter=ChangeFilter(project='chromium',
                                                       branch='master'),
                            treeStableTimer=60,
                            builderNames=[
                              'Win Builder',
                              'Mac Builder',
                              'Linux Builder',
                              'Android Builder',
                            ]),
  )
  specs = [
    {'name': 'Win Builder', 'category': 'win'},
    {'name': 'Win7 Tester', 'category': 'win'},
    {'name': 'Win7 Tester (long-running)', 'category': 'win'},
    {'name': 'Win8 Tester', 'category': 'win'},
    {'name': 'Win10 Tester', 'category': 'win'},
    {'name': 'Mac Builder', 'category': 'mac'},
    {'name': 'Mac Tester', 'category': 'mac'},
    {'name': 'Mac Tester (long-running)', 'category': 'mac'},
    {'name': 'Linux Builder', 'category': 'linux'},
    {'name': 'Linux Tester', 'category': 'linux'},
    {'name': 'Android Builder', 'category': 'android'},
    {'name': 'Android Tester', 'category': 'android'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_remote_run('chromium'),
        'category': spec['category'],
        'notify_on_missing': True,
      } for spec in specs
  ])
