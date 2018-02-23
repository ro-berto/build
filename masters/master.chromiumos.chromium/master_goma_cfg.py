# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory.chromeos_factory import ChromiteRecipeFactory

from buildbot.schedulers.basic import SingleBranchScheduler as Scheduler

def Builder(active_master, board):
  config = '%s-goma-canary-chromium-pfq-informational' % (board,)
  builder = {
      'name': config,
      'builddir': config,
      'category': '6goma canary',
      'factory': ChromiteRecipeFactory.remote(
          active_master, ChromiteRecipeFactory.PUBLIC, 'cros/cbuildbot'),
      'gatekeeper': 'pfq',
      'scheduler': 'chromium_cros_goma',
      'notify_on_missing': True,
      'properties': {
          'cbb_config': config,
      },
  }
  return builder


def Update(_config, active_master, c):
  builders = [
      Builder(active_master, 'amd64-generic'),
  ]

  c['schedulers'] += [
      Scheduler(name='chromium_cros_goma',
                branch='master',
                treeStableTimer=60,
                builderNames=[b['name'] for b in builders],
      ),
  ]
  c['builders'] += builders
