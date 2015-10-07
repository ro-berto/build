# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Nightly
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='webrtc_linux_scheduler',
                            branch='master',
                            treeStableTimer=0,
                            builderNames=[
                                'Linux32 ARM',
                                'Linux64 Release (swarming)',
                                'Linux Tsan v2 (parallel)',
      ]),
      # Run WebRTC DEPS roller every EMEA morning at 4am, 12pm and 8pm.
      Nightly(
          name='webrtc_deps',
          branch=None,
          builderNames=['Auto-roll - WebRTC DEPS'],
          hour=[19,3,11],
      ),
  ])

  specs = [
    {
      'name': 'Linux32 ARM',
      'slavebuilddir': 'linux_arm',
    },
    {
      'name': 'Linux Tsan v2 (parallel)',
      'slavebuilddir': 'linux_tsan2',
    },
    {
      'name': 'Linux64 Release (swarming)',
      'slavebuilddir': 'linux_swarming',
    },
    {
      'name': 'Auto-roll - WebRTC DEPS',
      'recipe': 'webrtc/auto_roll_webrtc_deps',
      'slavebuilddir': 'linux_autoroll',
    },
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory(spec.get('recipe',
                                                    'webrtc/standalone')),
        'notify_on_missing': True,
        'category': 'linux',
        'slavebuilddir': spec['slavebuilddir'],
        'auto_reboot': False,
      } for spec in specs
  ])
