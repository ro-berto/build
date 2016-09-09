# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.changes.filter import ChangeFilter
from buildbot.scheduler import Periodic
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import remote_run_factory

import master_site_config
ActiveMaster = master_site_config.ChromiumWebRTCFYI


def m_remote_run_chromium_src(recipe, **kwargs):
  return remote_run_factory.RemoteRunFactory(
      active_master=ActiveMaster,
      repository='https://chromium.googlesource.com/chromium/src.git',
      recipe=recipe,
      factory_properties={'path_config': 'kitchen'},
      use_gitiles=True,
      **kwargs)


def Update(c):
  hourly_builders = [
    'Android Builder (dbg)',
    'Android Builder ARM64 (dbg)',
    'Linux Builder',
    'Mac Builder',
  ]
  win_builders = [
    'Win Builder',
  ]
  all_builders = hourly_builders + win_builders

  c['schedulers'].extend([
      SingleBranchScheduler(name='webrtc_scheduler',
                            change_filter=ChangeFilter(project='webrtc',
                                                       branch='master'),
                            treeStableTimer=0,
                            builderNames=all_builders),
      Periodic(name='hourly_periodic_scheduler',
               periodicBuildTimer=60*60,
               builderNames=hourly_builders),
      Periodic(name='4hours_periodic_scheduler',
               periodicBuildTimer=4*60*60,
               builderNames=win_builders),
  ])

  specs = [
    {'name': 'Win Builder', 'category': 'win'},
    {'name': 'Win7 Tester', 'category': 'win'},
    {'name': 'Win10 Tester', 'category': 'win'},
    {'name': 'Mac Builder', 'category': 'mac'},
    {'name': 'Mac Tester', 'category': 'mac'},
    {'name': 'Linux Builder', 'category': 'linux'},
    {'name': 'Linux Tester', 'category': 'linux'},
    {'name': 'Android Builder (dbg)', 'category': 'android'},
    {
      'name': 'Android Builder ARM64 (dbg)',
      'category': 'android',
      'slavebuilddir': 'android_arm64',
    },
    {'name': 'Android Tests (dbg) (K Nexus5)', 'category': 'android'},
    {'name': 'Android Tests (dbg) (L Nexus5)', 'category': 'android'},
    {'name': 'Android Tests (dbg) (L Nexus6)', 'category': 'android'},
    {'name': 'Android Tests (dbg) (L Nexus7.2)', 'category': 'android'},
    {'name': 'Android Tests (dbg) (L Nexus9)', 'category': 'android'},
  ]

  for spec in specs:
    builder_dict = {
      'name': spec['name'],
      'factory': m_remote_run_chromium_src('chromium'),
      'category': spec['category'],
      'notify_on_missing': True,
    }
    if 'slavebuilddir' in spec:
      builder_dict['slavebuilddir'] = spec['slavebuilddir']

    c['builders'].append(builder_dict)
