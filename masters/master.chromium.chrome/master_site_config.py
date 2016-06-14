# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class ChromiumChrome(Master.Master1):
  project_name = 'Chromium Chrome'
  master_port = 8015
  slave_port = 8115
  master_port_alt = 8215
  buildbot_url = 'http://build.chromium.org/p/chromium.chrome/'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'chromium.chrome'
