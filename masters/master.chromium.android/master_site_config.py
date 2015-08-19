# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# pylint: disable=line-too-long

# This file was generated from
# scripts/tools/buildbot_tool_templates/master_site_config.py
# by "scripts/tools/buildbot-tool gen masters/master.chromium.android".
# DO NOT EDIT BY HAND!


"""ActiveMaster definition."""

from config_bootstrap import Master

class ChromiumAndroid(Master.Master1):
  project_name = 'ChromiumAndroid'
  master_port = 20101
  slave_port = 30101
  master_port_alt = 40101
  buildbot_url = 'https://build.chromium.org/p/chromium.android/'
  buildbucket_bucket = None
  service_account_file = None
