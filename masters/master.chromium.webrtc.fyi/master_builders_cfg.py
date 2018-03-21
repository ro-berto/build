# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.changes.filter import ChangeFilter
from buildbot.scheduler import Periodic
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import remote_run_factory
from master.factory import annotator_factory

import master_site_config
ActiveMaster = master_site_config.ChromiumWebRTCFYI


m_annotator = annotator_factory.AnnotatorFactory()


def m_remote_run(recipe, **kwargs):
  return remote_run_factory.RemoteRunFactory(
      active_master=ActiveMaster,
      repository='https://chromium.googlesource.com/chromium/tools/build.git',
      recipe=recipe,
      factory_properties={'path_config': 'kitchen'},
      **kwargs)


def Update(c):
  hourly_builders = [
    'Android Builder',
    'Android Builder (dbg)',
    'Android Builder ARM64 (dbg)',
    'Linux Builder',
    'Linux Builder (dbg)',
    'Mac Builder',
    'Mac Builder (dbg)',
    'ios-device',
    'ios-simulator',
  ]
  win_builders = [
    'Win Builder',
    'Win Builder (dbg)',
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
    {'name': 'Win Builder (dbg)', 'category': 'win'},
    {'name': 'Win7 Tester', 'category': 'win'},
    {'name': 'Win8 Tester', 'category': 'win'},
    {'name': 'Win10 Tester', 'category': 'win'},
    {'name': 'Mac Builder', 'category': 'mac', 'slavebuilddir': 'mac64'},
    {'name': 'Mac Builder (dbg)', 'category': 'mac', 'slavebuilddir': 'mac64'},
    {'name': 'Mac Tester', 'category': 'mac'},
    {
      'name': 'ios-device',
      'category': 'ios',
      'recipe': 'webrtc/chromium_ios',
      'slavebuilddir': 'mac64',
    },
    {
      'name': 'ios-simulator',
      'category': 'ios',
      'recipe': 'webrtc/chromium_ios',
      'slavebuilddir': 'mac64',
    },
    {'name': 'Linux Builder', 'category': 'linux'},
    {'name': 'Linux Builder (dbg)', 'category': 'linux'},
    {'name': 'Linux Tester', 'category': 'linux'},
    {'name': 'Android Builder', 'category': 'android'},
    {'name': 'Android Builder (dbg)', 'category': 'android'},
    {
      'name': 'Android Builder ARM64 (dbg)',
      'category': 'android',
      'slavebuilddir': 'android_arm64',
    },
    {'name': 'Android Tests (dbg) (K Nexus5)', 'category': 'android'},
    {'name': 'Android Tests (dbg) (N Nexus5X)', 'category': 'android'},
  ]

  for spec in specs:
    recipe = spec.get('recipe', 'chromium')
    builder_dict = {
      'name': spec['name'],
      'factory': m_annotator.BaseFactory(recipe) if 'ios' in recipe else
          m_remote_run(recipe),
      'category': spec['category'],
      'notify_on_missing': True,
    }
    if 'slavebuilddir' in spec:
      builder_dict['slavebuilddir'] = spec['slavebuilddir']

    c['builders'].append(builder_dict)
