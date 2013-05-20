# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Linux Tryserver definition."""

from config_bootstrap import Master

class TryServerLinux(Master.Master4):
  project_name = 'chromium.tryserver.linux'
  master_port = 8045
  slave_port = 8145
  master_port_alt = 8245
  try_job_port = 8345
  # Select tree status urls and codereview location.
  base_app_url = 'https://chromium-status.appspot.com'
  tree_status_url = base_app_url + '/status'
  store_revisions_url = base_app_url + '/revisions'
  last_good_url = base_app_url + '/lkgr'
  svn_url = 'svn://svn.chromium.org/chrome-try/try'
  reply_to = 'chrome-troope%s+tryserver@google.com' % 'rs'
