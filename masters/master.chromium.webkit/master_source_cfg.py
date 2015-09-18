# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import AnyBranchScheduler

from master import gitiles_poller


def Update(config, _active_master, c):
  # Polls config.Master.trunk_url for changes
  cr_poller = gitiles_poller.GitilesPoller(
      'https://chromium.googlesource.com/chromium/src',
      pollInterval=30, project='chromium')
  c['change_source'].append(cr_poller)

  c['schedulers'].append(AnyBranchScheduler(
      name='global_scheduler', branches=['trunk', 'master'], treeStableTimer=60,
      builderNames=[]))
