# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Periodic
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  buildernames_list = [
      'Mac Builder',
      'Mac GN',
      'Mac GN (dbg)',
  ]
  c['schedulers'].extend([
      SingleBranchScheduler(name='mac_webrtc_scheduler',
                            branch='master',
                            treeStableTimer=0,
                            builderNames=buildernames_list),
      Periodic(name='mac_periodic_scheduler',
               periodicBuildTimer=60*60,
               builderNames=buildernames_list),
  ])
  specs = [
    {'name': 'Mac Builder'},
    {'name': 'Mac Tester'},
    {
      'name': 'Mac GN',
      'recipe': 'chromium_gn',
      'slavebuilddir': 'mac_gn',
    },
    {
      'name': 'Mac GN (dbg)',
      'recipe': 'chromium_gn',
      'slavebuilddir': 'mac_gn',
    },
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory(spec.get('recipe',
                                                    'webrtc/chromium')),
        'category': 'mac',
        'notify_on_missing': True,
        'slavebuilddir': spec.get('slavebuilddir', 'mac'),
      } for spec in specs
  ])
