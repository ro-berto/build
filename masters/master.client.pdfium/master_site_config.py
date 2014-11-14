# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class Pdfium(Master.Master3):
  project_name = 'Pdfium'
  project_url = 'https://code.google.com/p/pdfium/'
  master_port = 30300
  slave_port = 40300
  master_port_alt = 50300
  buildbot_url = 'http://build.chromium.org/p/master.pdfium/'
