# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromeos_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory

# CrOS perf bots below.
defaults['category'] = '5chromiumos perf'

_PERF_SCHEDULER_NAME = 'chromium_src_perf'
helper.Scheduler(_PERF_SCHEDULER_NAME, branch='master', treeStableTimer=60)

def Builder(board, root):
  config = '%s-telemetry' % (board,)
  B(config,
    factory=config,
    gatekeeper='crosperf',
    builddir=config,
    scheduler=_PERF_SCHEDULER_NAME,
    notify_on_missing=True)
  F(config,
    chromeos_factory.CbuildbotFactory(
      buildroot='/b/cbuild/%s' % root,
      pass_revision=True,
      params=config).get_factory())


Builder('x86-generic', 'shared_external')
Builder('amd64-generic', 'shared_external')

def Update(_config, _active_master, c):
  return helper.Update(c)

