# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_public import Master3

class Libyuv(Master3):
  project_name = 'Libyuv'
  master_port = 8062
  slave_port = 8162
  master_port_alt = 8262
  server_url = 'http://libyuv.googlecode.com'
  project_url = 'http://libyuv.googlecode.com'
  from_address = 'libyuv-cb-watchlist@google.com'
  permitted_domains = ('google.com', 'chromium.org', 'webrtc.org')
