# Copyright (c) 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master.url_poller import URLPoller


LKGR_URL = 'https://chromium-status.appspot.com/lkgr'

def Update(config, active_master, c):
  c['change_source'].append(
      URLPoller(changeurl=LKGR_URL, pollInterval=300,
                category='lkgr', include_revision=True))
