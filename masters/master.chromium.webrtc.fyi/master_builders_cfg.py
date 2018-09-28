# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.changes.filter import ChangeFilter
from buildbot.scheduler import Periodic
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import remote_run_factory

import master_site_config
ActiveMaster = master_site_config.ChromiumWebRTCFYI


def m_remote_run(recipe, **kwargs):
  return remote_run_factory.RemoteRunFactory(
      active_master=ActiveMaster,
      repository='https://chromium.googlesource.com/chromium/tools/build.git',
      recipe=recipe,
      factory_properties={'path_config': 'kitchen'},
      **kwargs)


def Update(c):
  hourly_builders = [
    'WebRTC Chromium FYI Android Builder',
    'WebRTC Chromium FYI Android Builder (dbg)',
    'WebRTC Chromium FYI Android Builder ARM64 (dbg)',
    'WebRTC Chromium FYI Linux Builder',
    'WebRTC Chromium FYI Linux Builder (dbg)',
    'WebRTC Chromium FYI Mac Builder',
    'WebRTC Chromium FYI Mac Builder (dbg)',
    'WebRTC Chromium FYI ios-device',
    'WebRTC Chromium FYI ios-simulator',
  ]
  win_builders = [
    'WebRTC Chromium FYI Win Builder',
    'WebRTC Chromium FYI Win Builder (dbg)',
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
    {'name': 'WebRTC Chromium FYI Win Builder', 'category': 'win'},
    {'name': 'WebRTC Chromium FYI Win Builder (dbg)', 'category': 'win'},
    {'name': 'WebRTC Chromium FYI Win7 Tester', 'category': 'win'},
    {'name': 'WebRTC Chromium FYI Win8 Tester', 'category': 'win'},
    {'name': 'WebRTC Chromium FYI Win10 Tester', 'category': 'win'},
    {'name': 'WebRTC Chromium FYI Mac Builder', 'category': 'mac', 'slavebuilddir': 'mac64'},
    {'name': 'WebRTC Chromium FYI Mac Builder (dbg)', 'category': 'mac', 'slavebuilddir': 'mac64'},
    {'name': 'WebRTC Chromium FYI Mac Tester', 'category': 'mac'},
    {
      'name': 'WebRTC Chromium FYI ios-device',
      'category': 'ios',
      'recipe': 'webrtc/chromium_ios',
      'slavebuilddir': 'mac64',
    },
    {
      'name': 'WebRTC Chromium FYI ios-simulator',
      'category': 'ios',
      'recipe': 'webrtc/chromium_ios',
      'slavebuilddir': 'mac64',
    },
    {'name': 'WebRTC Chromium FYI Linux Builder', 'category': 'linux'},
    {'name': 'WebRTC Chromium FYI Linux Builder (dbg)', 'category': 'linux'},
    {'name': 'WebRTC Chromium FYI Linux Tester', 'category': 'linux'},
    {'name': 'WebRTC Chromium FYI Android Builder', 'category': 'android'},
    {'name': 'WebRTC Chromium FYI Android Builder (dbg)', 'category': 'android'},
    {
      'name': 'WebRTC Chromium FYI Android Builder ARM64 (dbg)',
      'category': 'android',
      'slavebuilddir': 'android_arm64',
    },
    {'name': 'WebRTC Chromium FYI Android Tests (dbg) (K Nexus5)', 'category': 'android'},
    {'name': 'WebRTC Chromium FYI Android Tests (dbg) (M Nexus5X)', 'category': 'android'},
  ]

  for spec in specs:
    recipe = spec.get('recipe', 'chromium')
    builder_dict = {
      'name': spec['name'],
      'factory': m_remote_run(recipe),
      'category': spec['category'],
      'notify_on_missing': True,
    }
    if 'slavebuilddir' in spec:
      builder_dict['slavebuilddir'] = spec['slavebuilddir']

    c['builders'].append(builder_dict)
