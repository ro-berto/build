# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class Dart(Master.Master3):
  base_app_url = 'https://dart-status.appspot.com'
  tree_status_url = base_app_url + '/status'
  store_revisions_url = base_app_url + '/revisions'
  last_good_url = base_app_url + '/lkgr'
  project_name = 'Dart'
  master_port = 20308
  slave_port = 30308
  # Enable when there's a public waterfall.
  master_port_alt = 25308
  buildbot_url = 'http://build.chromium.org/p/client.dart/'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'client.dart'
