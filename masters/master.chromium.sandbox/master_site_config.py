# Copyright (c) 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class ChromiumSandbox(Master.Master1):
  project_name = 'Chromium Sandbox'
  master_port = 20114
  slave_port = 30114
  master_port_alt = 25114
  buildbot_url = 'http://build.chromium.org/p/chromium.sandbox/'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'chromium.sandbox'
