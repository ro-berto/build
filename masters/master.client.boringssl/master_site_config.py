# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This file was generated from
# scripts/tools/buildbot_tool_templates/master_site_config.py
# by "../../build/scripts/tools/buildbot-tool gen .".
# DO NOT EDIT BY HAND!


"""ActiveMaster definition."""

from config_bootstrap import Master

class Boringssl(Master.Master3):
  project_name = 'Boringssl'
  master_port = 20311
  slave_port = 30311
  master_port_alt = 25311
  buildbot_url = 'https://build.chromium.org/p/client.boringssl/'
  buildbucket_bucket = None
  service_account_file = None
  # To enable outbound pubsub event streaming.
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'client.boringssl'
