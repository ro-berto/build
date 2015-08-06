# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class TryServerANGLE(Master.Master4a):
  project_name = 'ANGLE Try Server'
  master_port = 8090
  slave_port = 8190
  master_port_alt = 8290
  buildbot_url = 'http://build.chromium.org/p/tryserver.chromium.angle/'
  gerrit_host = 'https://chromium-review.googlesource.com'
