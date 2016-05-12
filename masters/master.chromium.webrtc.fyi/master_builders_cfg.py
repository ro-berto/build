# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.changes.filter import ChangeFilter
from buildbot.scheduler import Periodic
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  hourly_builders = [
    'Android Builder (dbg)',
    'Android Builder ARM64 (dbg)',
    'Linux Builder',
    'Mac Builder',
    'Mac GN',
    'Mac GN (dbg)',
  ]
  win_builders = [
    'Win Builder',
    'Win x64 GN',
    'Win x64 GN (dbg)',
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
    {
      'name': 'Win x64 GN',
      'category': 'win',
      'slavebuilddir': 'win_gn',
    },
    {
      'name': 'Win x64 GN (dbg)',
      'category': 'win',
      'slavebuilddir': 'win_gn',
    },
    {'name': 'Mac Builder', 'category': 'mac'},
    {'name': 'Mac Tester', 'category': 'mac'},
    {
      'name': 'Mac GN',
      'category': 'mac',
      'slavebuilddir': 'mac_gn',
    },
    {
      'name': 'Mac GN (dbg)',
      'category': 'mac',
      'slavebuilddir': 'mac_gn',
    },
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
      'factory': m_annotator.BaseFactory(spec.get('recipe', 'chromium')),
      'category': spec['category'],
      'notify_on_missing': True,
    }
    if 'slavebuilddir' in spec:
      builder_dict['slavebuilddir'] = spec['slavebuilddir']

    c['builders'].append(builder_dict)
