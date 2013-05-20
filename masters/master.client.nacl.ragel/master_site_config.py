# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class NativeClientRagel(Master.NaClBase):
  project_name = 'NativeClientRagel'
  master_port = 8033
  slave_port = 8133
  master_port_alt = 8233
