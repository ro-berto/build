# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class LibyuvTryServer(Master.Master4):
  project_name = 'Libyuv Try Server'
  master_port = 8006
  slave_port = 8106
  master_port_alt = 8206
  try_job_port = 8306
  from_address = 'libyuv-cb-watchlist@google.com'
  reply_to = 'chrome-troopers+tryserver@google.com'
  code_review_site = 'https://codereview.chromium.org'
  buildbot_url = 'http://build.chromium.org/p/tryserver.libyuv/'
  service_account_file = 'service-account-libyuv.json'
  buildbucket_bucket = 'master.tryserver.libyuv'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'tryserver.libyuv'
