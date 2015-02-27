# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Triggerable
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='webrtc_linux_scheduler',
                            branch='trunk',
                            treeStableTimer=0,
                            builderNames=[
                                'Linux Asan Builder',
      ]),
      Triggerable(name='linux_trigger', builderNames=[
          'Linux Asan Tester (parallel)',
      ]),
  ])

  specs = [
    {
      'name': 'Linux Asan Builder',
      'triggers': ['linux_trigger'],
      'slavebuilddir': 'linux_asan',
    },
    {
      'name': 'Linux Asan Tester (parallel)',
      'slavebuilddir': 'linux_asan',
    },
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory('webrtc/standalone',
                                           triggers=spec.get('triggers')),
        'notify_on_missing': True,
        'category': 'linux',
        'slavebuilddir': spec['slavebuilddir'],
        'auto_reboot': False,
      } for spec in specs
  ])
