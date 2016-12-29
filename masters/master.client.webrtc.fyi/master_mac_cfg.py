# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

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
      SingleBranchScheduler(name='webrtc_mac_scheduler',
                            branch='master',
                            treeStableTimer=0,
                            builderNames=[
                                'Mac (swarming)',
                                'iOS64 Sim Debug (iOS 9.0)',
                            ]),
  ])

  specs = [
    {'name': 'Mac (swarming)', 'slavebuilddir': 'mac_swarming'},
    {
      'name': 'iOS64 Sim Debug (iOS 9.0)',
      'slavebuilddir': 'mac64',
      'recipe': 'webrtc/ios',
    },
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory(spec['recipe'])
                   if 'recipe' in spec and spec['recipe'] == 'webrtc/ios'
                   else m_remote_run(spec.get('recipe', 'webrtc/standalone')),
        'notify_on_missing': True,
        'category': 'mac',
        'slavebuilddir': spec['slavebuilddir'],
      } for spec in specs
  ])
