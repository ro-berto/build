# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import gitiles_poller


def Update(config, c):
  libyuv_repo_url = config.Master.git_server_url + '/libyuv/libyuv'
  poller = gitiles_poller.GitilesPoller(
      libyuv_repo_url,
      svn_branch='trunk',
      revlinktmpl='http://code.google.com/p/libyuv/source/detail?r=%s',
      svn_mode=True)
  c['change_source'].append(poller)
