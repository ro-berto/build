# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory.chromeos_factory import ChromiteRecipeFactory

from buildbot.schedulers.basic import SingleBranchScheduler as Scheduler

def Builder(active_master, board):
  config = '%s-tot-asan-informational' % (board,)
  builder = {
      'name': config,
      'builddir': config,
      'category': '4chromeos asan',
      'factory': ChromiteRecipeFactory.remote(
          active_master, ChromiteRecipeFactory.PUBLIC, 'cros/cbuildbot'),
      'gatekeeper': 'crosasantest',
      'scheduler': 'chromium_src_asan',
      'notify_on_missing': True,
      'properties': {
          'cbb_config': config,
      },
  }
  return builder


def Update(_config, active_master, c):
  builders = [
  ]

  c['schedulers'] += [
      Scheduler(name='chromium_src_asan',
                branch='master',
                treeStableTimer=60,
                builderNames=[b['name'] for b in builders],
      ),
  ]
  c['builders'] += builders
