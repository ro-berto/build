# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Private ActiveMaster definition for master.toolkit."""

from config_bootstrap import Master

class Toolkit(Master.Master3):
  project_name = 'Toolkit'
  project_url = 'http://github.com/toolkitchen/toolkit'
  master_port = 8044
  slave_port = 8144
  master_port_alt = 8244
