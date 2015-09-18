# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This file was generated from
# scripts/tools/buildbot_tool_templates/master_site_config.py
# by "../../build/scripts/tools/buildbot-tool gen .".
# DO NOT EDIT BY HAND!


"""ActiveMaster definition."""

from config_bootstrap import Master

class CustomTabsClientTryserver(Master.Master4a):
  project_name = 'CustomTabsClientTryserver'
  master_port = 20400
  slave_port = 30400
  master_port_alt = 40400
  buildbot_url = 'https://build.chromium.org/p/tryserver.client.custom_tabs_client/'
  buildbucket_bucket = 'master.tryserver.client.custom_tabs_client'
  service_account_file = 'service-account-chromium-tryserver.json'
