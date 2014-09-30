# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master.chromium_git_poller_bb8 import ChromiumGitPoller


def Update(config, active_master, c):
  syzygy_poller = ChromiumGitPoller(
      repourl='https://github.com/google/syzygy.git',
      branch='master',
      pollInterval=60)
  c['change_source'].append(syzygy_poller)
