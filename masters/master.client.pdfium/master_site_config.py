# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class Pdfium(Master.Master3):
  project_name = 'Pdfium'
  project_url = 'https://code.google.com/p/pdfium/'
  master_port = 20310
  slave_port = 30310
  master_port_alt = 40310
  buildbot_url = 'http://build.chromium.org/p/client.pdfium/'
