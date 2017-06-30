# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This file was generated from
# scripts/tools/buildbot_tool_templates/master_site_config.py
# by "../../build/scripts/tools/buildbot-tool gen .".
# DO NOT EDIT BY HAND!


"""ActiveMaster definition."""

from config_bootstrap import Master

class DartTryServer(Master.Master4a):
  project_name = 'DartTryServer'
  master_port = 21402
  slave_port = 31402
  master_port_alt = 26402
  buildbot_url = 'https://build.chromium.org/p/tryserver.client.dart/'
  buildbucket_bucket = 'master.tryserver.client.dart'
  service_account_file = 'service-account-dart-trybots.json'
  # To enable outbound pubsub event streaming.
  pubsub_service_account_file = 'luci-milo'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'tryserver.client.dart'
