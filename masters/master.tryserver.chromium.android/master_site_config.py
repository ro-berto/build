# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This file was generated from
# scripts/tools/buildbot_tool_templates/master_site_config.py
# by "../../build/scripts/tools/buildbot-tool gen .".
# DO NOT EDIT BY HAND!


"""ActiveMaster definition."""

from config_bootstrap import Master

class TryserverChromiumAndroid(Master.Master4a):
  project_name = 'TryserverChromiumAndroid'
  master_port = 21401
  slave_port = 31401
  master_port_alt = 41401
  buildbot_url = 'https://build.chromium.org/p/tryserver.chromium.android/'
  buildbucket_bucket = None
  service_account_file = None
