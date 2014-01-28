# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_public import ChromiumOSBase

class ChromiumOS(ChromiumOSBase):
  project_name = 'ChromiumOS'
  master_port = 8014
  slave_port = 8114
  master_port_alt = 8214
