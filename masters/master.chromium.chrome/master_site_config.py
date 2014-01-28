# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_public import Master1

class ChromiumChrome(Master1):
  project_name = 'Chromium Chrome'
  master_port = 8015
  slave_port = 8115
  master_port_alt = 8215
