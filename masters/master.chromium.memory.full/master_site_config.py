# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class ChromiumMemoryFull(Master.Master1):
  project_name = 'Chromium Memory Full'
  master_port = 20105
  slave_port = 30105
  master_port_alt = 25105
  buildbot_url = 'http://build.chromium.org/p/chromium.memory.full/'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'chromium.memory.full'
