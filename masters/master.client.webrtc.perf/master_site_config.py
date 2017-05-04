# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class WebRTCPerf(Master.Master3a):
  project_name = 'WebRTC Perf'
  master_port = 20309
  slave_port = 30309
  master_port_alt = 25309
  server_url = 'http://webrtc.googlecode.com'
  project_url = 'http://webrtc.googlecode.com'
  from_address = 'webrtc-cb-perf-watchlist@google.com'
  tree_closing_notification_recipients = ['webrtc-cb-perf-watchlist@google.com']
  master_domain = 'webrtc.org'
  permitted_domains = ('google.com', 'chromium.org', 'webrtc.org')
  buildbot_url = 'http://build.chromium.org/p/client.webrtc.perf/'
  service_account_file = 'service-account-webrtc.json'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'client.webrtc.perf'
