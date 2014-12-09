# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class Crashpad(Master.Master3):
  project_name = 'Crashpad'
  project_url = 'https://code.google.com/p/crashpad/'
  master_port = 20300
  slave_port = 30300
  master_port_alt = 40300
  buildbot_url = 'https://build.chromium.org/p/client.crashpad/'
