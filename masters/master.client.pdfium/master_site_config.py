# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class Pdfium(Master.Master3):
  project_name = 'Pdfium'
  project_url = 'https://code.google.com/p/pdfium/'
  master_port = 21411
  slave_port = 31411
  master_port_alt = 41411
  buildbot_url = 'http://build.chromium.org/p/master.pdfium/'
