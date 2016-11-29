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
      SingleBranchScheduler(name='webrtc_mac_scheduler',
                            branch='master',
                            treeStableTimer=0,
                            builderNames=[
                                'Mac (swarming)',
                            ]),
  ])

  specs = [
    {'name': 'Mac (swarming)', 'slavebuilddir': 'mac_swarming'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_remote_run('webrtc/standalone'),
        'notify_on_missing': True,
        'category': 'mac',
        'slavebuilddir': spec['slavebuilddir'],
      } for spec in specs
  ])
