# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This file was generated from
# scripts/tools/buildbot_tool_templates/master_site_config.py
# by "../../build/scripts/tools/buildbot-tool gen .".
# DO NOT EDIT BY HAND!


"""ActiveMaster definition."""

from config_bootstrap import Master

class InfraTryServer(Master.Master4a):
  project_name = 'InfraTryServer'
  master_port = 21402
  slave_port = 31402
  master_port_alt = 41402
  buildbot_url = 'https://build.chromium.org/p/tryserver.infra/'
  buildbucket_bucket = 'master.tryserver.infra'
  service_account_file = 'service-account-chromium-tryserver.json'
