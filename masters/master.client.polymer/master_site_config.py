# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition for master.client.polymer."""

from config_public import Master3

class Polymer(Master3):
  project_name = 'Polymer'
  project_url = 'http://github.com/Polymer/'
  master_port = 8044
  slave_port = 8144
  master_port_alt = 8244
