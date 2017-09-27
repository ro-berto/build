# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This file was generated from
# scripts/tools/buildbot_tool_templates/master_site_config.py
# by "../../build/scripts/tools/buildbot-tool gen .".
# DO NOT EDIT BY HAND!


"""ActiveMaster definition."""

from config_bootstrap import Master

class ClientV8Official(Master.Master3a):
  project_name = 'ClientV8Official'
  master_port = 21304
  slave_port = 31304
  master_port_alt = 26304
  buildbot_url = 'https://build.chromium.org/p/client.v8.official/'
  buildbucket_bucket = 'master.client.v8.official'
  service_account_file = 'service-account-v8.json'
  # To enable outbound pubsub event streaming.
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'client.v8.official'
