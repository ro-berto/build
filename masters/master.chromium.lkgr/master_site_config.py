# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_public import Master1

class ChromiumLKGR(Master1):
  project_name = 'Chromium LKGR'
  master_port = 8018
  slave_port = 8118
  master_port_alt = 8218
