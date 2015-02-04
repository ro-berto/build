# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Periodic
from buildbot.scheduler import Triggerable
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  buildernames_list = [
      'Android Builder (dbg)',
      'Android Builder ARM64 (dbg)',
      'Android GN',
      'Android GN (dbg)',
  ]
  c['schedulers'].extend([
      SingleBranchScheduler(name='android_webrtc_scheduler',
                            branch='trunk',
                            treeStableTimer=0,
                            builderNames=buildernames_list),
      Periodic(name='android_periodic_scheduler',
               periodicBuildTimer=30*60,
               builderNames=buildernames_list),
      Triggerable(name='android_trigger_dbg', builderNames=[
          'Android Tests (dbg) (L Nexus5)',
          'Android Tests (dbg) (L Nexus7.2)',
      ]),
      Triggerable(name='android_trigger_arm64_dbg', builderNames=[
          'Android Tests (dbg) (L Nexus9)',
      ]),
  ])

  specs = [
    {
      'name': 'Android Builder (dbg)',
      'triggers': ['android_trigger_dbg'],
    },
    {
      'name': 'Android Builder ARM64 (dbg)',
      'triggers': ['android_trigger_arm64_dbg'],
      'slavebuilddir': 'android_arm64',
    },
    {'name': 'Android Tests (dbg) (L Nexus5)'},
    {'name': 'Android Tests (dbg) (L Nexus7.2)'},
    {'name': 'Android Tests (dbg) (L Nexus9)'},
    {
      'name': 'Android GN',
      'slavebuilddir': 'android_gn',
    },
    {
      'name': 'Android GN (dbg)',
      'slavebuilddir': 'android_gn',
    },
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory(
            'webrtc/chromium',
            triggers=spec.get('triggers')),
        'category': 'android',
        'notify_on_missing': True,
        'slavebuilddir': spec.get('slavebuilddir', 'android'),
      } for spec in specs
  ])
