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

def m_remote_run(recipe, **kwargs):
  return remote_run_factory.RemoteRunFactory(
      active_master=ActiveMaster,
      repository='https://chromium.googlesource.com/chromium/tools/build.git',
      recipe=recipe,
      factory_properties={'path_config': 'kitchen'},
      **kwargs)

def Update(_config, active_master, c):
  c['schedulers'].extend([
      SingleBranchScheduler(
          name='chromeos_asan_rel',
          branch='master',
          treeStableTimer=60,
          builderNames=['Linux Chromium OS ASan LSan Builder']),
      Triggerable(
          name='chromeos_asan_rel_trigger',
          builderNames=['Linux Chromium OS ASan LSan Tests (1)']),
  ])

  specs = [
    {
      'name': 'Linux Chromium OS ASan LSan Builder',
      'triggers': ['chromeos_asan_rel_trigger']
    },
    {'name': 'Linux Chromium OS ASan LSan Tests (1)'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_remote_run(
            'chromium', triggers=spec.get('triggers')),
        'notify_on_missing': True,
        'category': '3chromeos asan',
      } for spec in specs
  ])
