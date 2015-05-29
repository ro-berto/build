# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This file was generated from
# scripts/tools/buildbot_tool_templates/master_site_config.py
# by "scripts/tools/buildbot-tool gen masters/master.client.gyp".
# DO NOT EDIT BY HAND!


"""ActiveMaster definition."""

from config_bootstrap import Master

class GYP(Master.Master3):
  project_name = 'GYP'
  master_port = 20302
  slave_port = 30302
  master_port_alt = 40302
  buildbot_url = 'https://build.chromium.org/p/client.gyp/'
  buildbucket_bucket = None
  service_account_file = None
