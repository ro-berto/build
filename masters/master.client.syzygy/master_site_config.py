# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

class Syzygy(object):
  project_name = 'Syzygy'
  master_port = 8042
  slave_port = 8142
  master_port_alt = 8242
  tree_closing_notification_recipients = []
  from_address = 'buildbot@chromium.org'
  master_host = 'master3.golo.chromium.org'
  buildslave_version = 'buildbot_slave_8_4'
  twisted_version = 'twisted_10_2'
