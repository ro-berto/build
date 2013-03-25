# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Private ActiveMaster definition for master.toolkit."""

import socket

class Toolkit(object):
  project_name = 'Toolkit'
  project_url = 'http://github.com/toolkitchen/toolkit'
  master_port = 8044
  slave_port = 8144
  master_port_alt = 8244
  tree_closing_notification_recipients = []
  from_address = 'buildbot@chromium.org'
  master_host = 'master3.golo.chromium.org'
  is_production_host = socket.getfqdn() == master_host
