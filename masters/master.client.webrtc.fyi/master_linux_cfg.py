# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Nightly
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory
from master.factory import remote_run_factory

import master_site_config
ActiveMaster = master_site_config.WebRTCFYI


def m_remote_run(recipe, **kwargs):
  return remote_run_factory.RemoteRunFactory(
      active_master=ActiveMaster,
      repository='https://chromium.googlesource.com/chromium/tools/build.git',
      recipe=recipe,
      factory_properties={'path_config': 'kitchen'},
      **kwargs)


m_annotator = annotator_factory.AnnotatorFactory()


def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='webrtc_linux_scheduler',
                            branch='master',
                            treeStableTimer=0,
                            builderNames=[
                                'Linux Memcheck (swarming)',
                                'Linux64 GCC',
      ]),
      # Run WebRTC DEPS roller at CET hours: 4am, 12pm and 8pm.
      Nightly(
          name='webrtc_deps',
          branch=None,
          builderNames=['Auto-roll - WebRTC DEPS'],
          hour=[19,3,11],  # Pacific timezone.
      ),
  ])

  specs = [
    {'name': 'Linux64 GCC', 'slavebuilddir': 'linux_gcc'},
    {'name': 'Linux Memcheck (swarming)', 'slavebuilddir': 'linux_memcheck'},
    {
      'name': 'Auto-roll - WebRTC DEPS',
      'recipe': 'webrtc/auto_roll_webrtc_deps',
      'slavebuilddir': 'linux_autoroll',
    },
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory(spec['recipe'])
                   if 'recipe' in spec
                   else m_remote_run('webrtc/standalone'),
        'notify_on_missing': True,
        'category': 'linux',
        'slavebuilddir': spec['slavebuilddir'],
        'auto_reboot': False,
      } for spec in specs
  ])
