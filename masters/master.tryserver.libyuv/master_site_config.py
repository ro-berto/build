# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

import socket


class LibyuvTryServer(object):
  project_name = 'Libyuv Try Server'
  master_port = 8006
  slave_port = 8106
  master_port_alt = 8206
  try_job_port = 8306
  from_address = 'libyuv-cb-watchlist@google.com'
  code_review_site = 'http://review.webrtc.org'
  master_host = 'master4.golo.chromium.org'
  is_production_host = socket.getfqdn() == master_host
  svn_url = 'svn://svn.chromium.org/chrome-try/try-libyuv'
