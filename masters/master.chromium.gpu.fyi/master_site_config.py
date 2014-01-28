# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_public import Master1

class ChromiumGPUFYI(Master1):
  project_name = 'Chromium GPU FYI'
  master_port = 8017
  slave_port = 8117
  master_port_alt = 8217
