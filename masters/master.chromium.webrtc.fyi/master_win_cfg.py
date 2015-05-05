# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Periodic
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  buildernames_list = [
      'Win Builder',
      'Win GN',
      'Win GN (dbg)',
  ]
  c['schedulers'].extend([
      SingleBranchScheduler(name='win_webrtc_scheduler',
                            branch='master',
                            treeStableTimer=0,
                            builderNames=buildernames_list),
      Periodic(name='win_periodic_scheduler',
               periodicBuildTimer=4*60*60,
               builderNames=buildernames_list),
  ])
  specs = [
    {'name': 'Win Builder'},
    {'name': 'WinXP Tester'},
    {'name': 'Win7 Tester'},
    {
      'name': 'Win GN',
      'recipe': 'chromium_gn',
      'slavebuilddir': 'win_gn',
    },
    {
      'name': 'Win GN (dbg)',
      'recipe': 'chromium_gn',
      'slavebuilddir': 'win_gn',
    },
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory(
            spec.get('recipe', 'webrtc/chromium'),
            triggers=spec.get('triggers')),
        'category': 'win',
        'notify_on_missing': True,
        'slavebuilddir': spec.get('slavebuilddir', 'win'),
      } for spec in specs
  ])
