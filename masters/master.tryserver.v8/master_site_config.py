# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class V8TryServer(Master.Master4):
  project_name = 'V8 Try Server'
  master_port = 8007
  slave_port = 8107
  master_port_alt = 8207
  try_job_port = 8307
  from_address = 'v8-dev@googlegroups.com'
  reply_to = 'chrome-troopers+tryserver@google.com'
  svn_url = 'svn://svn.chromium.org/chrome-try-v8'
  base_app_url = 'https://v8-status.appspot.com'
  tree_status_url = base_app_url + '/status'
  store_revisions_url = base_app_url + '/revisions'
  last_good_url = base_app_url + '/lkgr'
  code_review_site = 'http://codereview.chromium.org'
