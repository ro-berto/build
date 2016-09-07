# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.process.properties import WithProperties
from buildbot.scheduler import Triggerable
from buildbot.schedulers.basic import SingleBranchScheduler

from master import master_utils
from master.factory import remote_run_factory

import master_site_config

ActiveMaster = master_site_config.ChromiumMemory

revision_getter = master_utils.ConditionalProperty(
    lambda build: build.getProperty('revision'),
    WithProperties('%(revision)s'),
    'master')

def m_remote_run_chromium_src(recipe, **kwargs):
  kwargs.setdefault('revision', revision_getter)
  return remote_run_factory.RemoteRunFactory(
      active_master=ActiveMaster,
      repository='https://chromium.googlesource.com/chromium/src.git',
      recipe=recipe,
      factory_properties={'path_config': 'kitchen'},
      use_gitiles=True,
      **kwargs)

def Update(_config, active_master, c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='linux_asan_rel',
                            branch='master',
                            treeStableTimer=60,
                            builderNames=[
          'Linux ASan LSan Builder'
      ]),
      Triggerable(name='linux_asan_rel_trigger', builderNames=[
          'Linux ASan LSan Tests (1)',
          'Linux ASan Tests (sandboxed)',
      ]),
  ])
  specs = [
    {
      'name': 'Linux ASan LSan Builder',
      'triggers': ['linux_asan_rel_trigger'],
    },
    {'name': 'Linux ASan LSan Tests (1)'},
    {'name': 'Linux ASan Tests (sandboxed)'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_remote_run_chromium_src(
            'chromium', triggers=spec.get('triggers')),
        'notify_on_missing': True,
        'category': '1linux asan lsan',
      } for spec in specs
  ])
