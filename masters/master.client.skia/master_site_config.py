# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""


from config_bootstrap import Master


class Skia(Master.Master3):
  project_name = 'Skia'
  master_port = 8041
  slave_port = 8141
  master_port_alt = 8241
  repo_url = 'https://skia.googlesource.com/skia.git'
  production_host = None
  is_production_host = False
