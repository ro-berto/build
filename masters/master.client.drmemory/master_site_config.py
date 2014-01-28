# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_public import Master3

class DrMemory(Master3):
  project_name = 'DrMemory'
  master_port = 8058
  slave_port = 8158
  master_port_alt = 8258
