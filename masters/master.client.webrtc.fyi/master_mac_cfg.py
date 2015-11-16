# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='webrtc_mac_scheduler',
                            branch='master',
                            treeStableTimer=0,
                            builderNames=[
                                'Mac64 Release (swarming)',
                                'iOS64 Debug (GN)',
                                'iOS64 Release (GN)',
                            ]),
  ])

  specs = [
    {'name': 'Mac64 Release (swarming)', 'slavebuilddir': 'mac_swarming'},
    {'name': 'iOS64 Debug (GN)', 'slavebuilddir': 'mac64_gn'},
    {'name': 'iOS64 Release (GN)', 'slavebuilddir': 'mac64_gn'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory('webrtc/standalone'),
        'notify_on_missing': True,
        'category': 'mac',
        'slavebuilddir': spec['slavebuilddir'],
      } for spec in specs
  ])
