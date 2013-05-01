# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Linux Tryserver definition."""

import socket


class _Master4(object):
  """Try server master."""
  master_host = 'master4.golo.chromium.org'
  is_production_host = socket.getfqdn() == 'master4.golo.chromium.org'
  tree_closing_notification_recipients = []
  from_address = 'tryserver@chromium.org'
  reply_to = 'chrome-troope%s+tryserver@google.com' % 'rs'
  code_review_site = 'https://chromiumcodereview.appspot.com'
  buildslave_version = 'buildbot_slave_8_4'
  twisted_version = 'twisted_10_2'


class TryServerLinux(_Master4):
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
