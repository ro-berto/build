# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import gitiles_poller


def Update(config, c):
  webrtc_repo_url = config.Master.git_server_url + '/external/webrtc'
  poller = gitiles_poller.GitilesPoller(
      webrtc_repo_url,
      svn_branch='trunk',
      svn_mode=True)
  c['change_source'].append(poller)
