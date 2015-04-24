# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class InfraCron(Master.Master1):
  project_name = 'InfraCron'
  master_port_id = 12
  buildbot_url = 'https://build.chromium.org/p/chromium.infra.cron/'
  service_account_file = 'service-account-infra-cron.json'
  buildbucket_bucket = 'master.chromium.infra.cron'
