# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from common import chromium_utils

from master import chromium_svn_poller
from master import gitiles_poller
from master import master_config

defaults = {}

helper = master_config.Helper(defaults)
helper.Scheduler('chromium_src', branch='src', treeStableTimer=60)

def Update(config, _active_master, c):
  poller = gitiles_poller.GitilesPoller(
    repo_url='https://chromium.googlesource.com/chromium/src',
    branches=['master'],
    revlinktmpl='https://chromium.googlesource.com/chromium/src/+/%s',
    pollInterval=10,
    svn_mode=False,
    change_filter=chromium_svn_poller.ChromiumChangeFilter,
  )
  c['change_source'].append(poller)
  return helper.Update(c)
