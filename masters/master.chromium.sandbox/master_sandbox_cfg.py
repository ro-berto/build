# Copyright (c) 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.process.properties import WithProperties
from buildbot.scheduler import Triggerable
from buildbot.schedulers.basic import SingleBranchScheduler

from master import master_utils
from master.factory import remote_run_factory

import master_site_config
ActiveMaster = master_site_config.ChromiumSandbox


def m_remote_run(recipe, **kwargs):
  return remote_run_factory.RemoteRunFactory(
      active_master=ActiveMaster,
      repository='https://chromium.googlesource.com/chromium/tools/build.git',
      recipe=recipe,
      factory_properties={'path_config': 'kitchen'},
      **kwargs)


def Update(_config, active_master, c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='linux_src',
                            branch='master',
                            treeStableTimer=60,
                            builderNames=[
          'Linux Builder SANDBOX',
          #'Linux Builder (dbg)(32) SANDBOX',
          #'Linux Builder (dbg) SANDBOX',
          #'Cast Linux SANDBOX',
          #'Cast Audio Linux SANDBOX',
          'Deterministic Linux SANDBOX',
          'Fuchsia x64 SANDBOX',
      ]),
  ])

  # name (str): required, must match string in schedulers above
  # recipe (str): optional (default: 'chromium'), the recipe to use for
  #   this builder.
  specs = [
    {'name': 'Linux Builder SANDBOX'},
    {'name': 'Linux Tests SANDBOX'},   # Triggered by above builder.
    # {'name': 'Linux Builder (dbg)(32) SANDBOX'},
    # {'name': 'Linux Tests (dbg)(1)(32) SANDBOX'},
    # {'name': 'Linux Builder (dbg) SANDBOX'},
    # {'name': 'Linux Tests (dbg)(1) SANDBOX'},
    # {'name': 'Cast Linux SANDBOX'},
    # {'name': 'Cast Audio Linux SANDBOX'},
    {'name': 'Deterministic Linux SANDBOX',
     'recipe': 'swarming/deterministic_build'},
    {'name': 'Fuchsia x64 SANDBOX'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_remote_run(spec.get('recipe', 'chromium')),
        'notify_on_missing': True,
        'category': '4linux',
      } for spec in specs
  ])
