# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.changes.filter import ChangeFilter
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

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
                            ]),
  )
  specs = [
    {'name': 'Win Builder', 'category': 'win'},
    {'name': 'WinXP Tester', 'category': 'win'},
    {'name': 'Win7 Tester', 'category': 'win'},
    {'name': 'Win8 Tester', 'category': 'win'},
    {'name': 'Win10 Tester', 'category': 'win'},
    {'name': 'Mac Builder', 'category': 'mac'},
    {'name': 'Mac Tester', 'category': 'mac'},
    {'name': 'Linux Builder', 'recipe': 'chromium', 'category': 'linux'},
    {'name': 'Linux Tester', 'recipe': 'chromium', 'category': 'linux'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory(spec.get('recipe',
                                                    'webrtc/chromium')),
        'category': spec['category'],
        'notify_on_missing': True,
      } for spec in specs
  ])

