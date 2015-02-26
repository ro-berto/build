# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class Boringssl(Master.Master3):
  project_name = 'Boringssl'
  project_url = 'https://boringssl.googlesource.com/boringssl/'
  master_port = 20311
  slave_port = 30311
  master_port_alt = 40311
  buildbot_url = 'http://build.chromium.org/p/client.boringssl/'
