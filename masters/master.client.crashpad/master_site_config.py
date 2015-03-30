# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This file was generated from
# scripts/tools/buildbot_tool_templates/master_site_config.py
# by "scripts/tools/buildbot-tool gen masters/master.client.crashpad".
# DO NOT EDIT BY HAND!


"""ActiveMaster definition."""

from config_bootstrap import Master

class ClientCrashpad(Master.Master3):
  project_name = 'ClientCrashpad'
  master_port = 20300
  slave_port = 30300
  master_port_alt = 40300
  buildbot_url = 'https://build.chromium.org/p/client.crashpad/'
