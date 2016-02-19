# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class Dartino(Master.Master3):
  base_app_url = 'https://dart-status.appspot.com'
  tree_status_url = base_app_url + '/status'
  store_revisions_url = base_app_url + '/revisions'
  project_name = 'Dart'
  master_port = 20316
  slave_port = 30316
  # Enable when there's a public waterfall.
  master_port_alt = 25316
  buildbot_url = 'http://build.chromium.org/p/client.fletch/'
