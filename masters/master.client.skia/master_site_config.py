# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""


from common.skia import global_constants
from config_bootstrap import Master
from master.skia import skia_master_utils


class Skia(Master.Master3):
  project_name = 'Skia'
  master_port = 8084
  slave_port = 8184
  master_port_alt = 8284
  repo_url = global_constants.SKIA_REPO
  buildbot_url = 'http://build.chromium.org/p/client.skia/'
  code_review_site = 'https://codereview.chromium.org'
  service_account_file = skia_master_utils.SERVICE_ACCOUNT_FILE
  buildbucket_bucket = 'master.client.skia'
