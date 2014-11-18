# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class MojoTryServer(Master.Master4a):
  project_name = 'Mojo Try Server'
  master_port = 21410
  slave_port = 31410
  master_port_alt = 41410
  buildbot_url = 'https://build.chromium.org/p/tryserver.client.mojo/'
  code_review_site = 'https://codereview.chromium.org'
