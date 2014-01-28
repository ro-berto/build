# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_public import Master1

class ChromiumWin(Master1):
  project_name = 'Chromium Win'
  master_port = 8085
  slave_port = 8185
  master_port_alt = 8285
