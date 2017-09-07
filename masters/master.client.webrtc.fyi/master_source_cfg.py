# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import gitiles_poller


def Update(config, c):
  webrtc_repo_url = 'https://webrtc.googlesource.com/src'
  poller = gitiles_poller.GitilesPoller(webrtc_repo_url)
  c['change_source'].append(poller)
