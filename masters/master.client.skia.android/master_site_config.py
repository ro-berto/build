# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""


from common.skia import global_constants
from config_bootstrap import Master


class SkiaAndroid(Master.Master3):
  project_name = 'SkiaAndroid'
  master_port = 8096
  slave_port = 8196
  master_port_alt = 8296
  repo_url = global_constants.SKIA_REPO
  buildbot_url = 'http://build.chromium.org/p/client.skia.android/'
  service_account_file = global_constants.SERVICE_ACCOUNT_FILE
  buildbucket_bucket = 'master.client.skia.android'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'client.skia.android'
