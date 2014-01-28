# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_public import Master1

class Chromium(Master1):
  project_name = 'Chromium'
  master_port = 8010
  slave_port = 8110
  master_port_alt = 8210
