# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.schedulers.basic import SingleBranchScheduler

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


def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='webrtc_windows_scheduler',
                            branch='master',
                            treeStableTimer=0,
                            builderNames=[
                                'Win64 Debug (Win8)',
                                'Win64 Debug (Win10)',
                            ]),
  ])

  specs = [
    {
      'name': 'Win64 Debug (Win8)',
      'slavebuilddir': 'win',
    },
    {
      'name': 'Win64 Debug (Win10)',
      'slavebuilddir': 'win',
    },
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_remote_run(spec.get('recipe', 'webrtc/standalone')),
        'notify_on_missing': True,
        'category': 'win',
        'slavebuilddir': spec['slavebuilddir'],
      } for spec in specs
  ])
