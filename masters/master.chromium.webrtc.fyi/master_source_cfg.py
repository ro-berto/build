# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import gitiles_poller


def Update(config, c):
  webrtc_repo_url = config.Master.git_server_url + '/external/webrtc/'
  webrtc_poller = gitiles_poller.GitilesPoller(webrtc_repo_url)
  c['change_source'].append(webrtc_poller)

  samples_poller = gitiles_poller.GitilesPoller(
      config.Master.git_server_url + '/external/webrtc-samples',
      comparator=webrtc_poller.comparator)
  c['change_source'].append(samples_poller)
