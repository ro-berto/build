# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class WebRTCPerf(Master.Master3):
  project_name = 'WebRTC Perf'
  master_port = 20301
  slave_port = 30301
  master_port_alt = 25301
  server_url = 'http://webrtc.googlecode.com'
  project_url = 'http://webrtc.googlecode.com'
  from_address = 'webrtc-cb-perf-watchlist@google.com'
  buildbot_url = 'http://build.chromium.org/p/client.webrtc.perf/'
  service_account_file = 'service-account-webrtc.json'
  buildbucket_bucket = 'master.client.webrtc.perf'
