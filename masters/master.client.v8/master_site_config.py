# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class V8(Master.Master3):
  project_name = 'V8'
  master_port = 8036
  slave_port = 8136
  master_port_alt = 8236
  project_url = 'http://v8.googlecode.com'
  perf_base_url = 'http://build.chromium.org/f/client/perf'
