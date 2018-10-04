# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Periodic
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory
from master.factory import remote_run_factory

import master_site_config
ActiveMaster = master_site_config.WebRTCFYI


INFRA_REPO_URL = 'https://chromium.googlesource.com/infra/infra'


def m_remote_run(recipe, **kwargs):
  properties = {'path_config': 'kitchen'}
  properties.update(kwargs.pop('properties', {}))
  return remote_run_factory.RemoteRunFactory(
      active_master=ActiveMaster,
      repository=kwargs.pop(
          'repository',
          'https://chromium.googlesource.com/chromium/tools/build.git'
      ),
      recipe=recipe,
      factory_properties=properties,
      **kwargs)


m_annotator = annotator_factory.AnnotatorFactory()


def Update(c):
  c['schedulers'].extend([
      # Update LKGR revision every 5 minutes.
      Periodic(
          name='webrtc_lkgr',
          periodicBuildTimer=5*60,
          branch=None,
          builderNames=[
              'WebRTC lkgr finder',
          ],
      ),
  ])

  specs = [
    {
      'name': 'WebRTC lkgr finder',
      'factory': m_remote_run(
          'lkgr_finder',
          repository=INFRA_REPO_URL,
          properties={'lkgr_project': 'webrtc', 'allowed_lag': 4},
      ),
      'slavebuilddir': 'webrtc_lkgr',
    },
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        # TODO(ehmaldonado): Flip all bots to remote run.
        'factory': spec['factory']
                   if 'factory' in spec
                   else m_annotator.BaseFactory(spec['recipe']),
        'notify_on_missing': True,
        'category': 'linux',
        'slavebuilddir': spec['slavebuilddir'],
        'auto_reboot': False,
      } for spec in specs
  ])
