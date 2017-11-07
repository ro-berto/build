# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.process.properties import WithProperties
from buildbot.scheduler import Triggerable
from buildbot.schedulers.basic import SingleBranchScheduler

from master import master_utils
from master.factory import remote_run_factory

import master_site_config
ActiveMaster = master_site_config.ChromiumLinux


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
          'Linux Builder',
          'Linux Builder (dbg)(32)',
          'Linux Builder (dbg)',
          'Cast Linux',
          'Cast Audio Linux',
          'Deterministic Linux',
          'Fuchsia ARM64',
          'Fuchsia x64',
      ]),
  ])

  # name (str): required, must match string in schedulers above
  # recipe (str): optional (default: 'chromium'), the recipe to use for
  #   this builder.
  specs = [
    {'name': 'Linux Builder'},
    {'name': 'Linux Tests'},
    {'name': 'Linux Builder (dbg)(32)'},
    {'name': 'Linux Tests (dbg)(1)(32)'},
    {'name': 'Linux Builder (dbg)'},
    {'name': 'Linux Tests (dbg)(1)'},
    {'name': 'Cast Linux'},
    {'name': 'Cast Audio Linux'},
    {'name': 'Deterministic Linux',
     'recipe': 'swarming/deterministic_build'},
    {'name': 'Fuchsia ARM64'},
    {'name': 'Fuchsia x64'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_remote_run(spec.get('recipe', 'chromium')),
        'notify_on_missing': True,
        'category': '4linux',
      } for spec in specs
  ])
