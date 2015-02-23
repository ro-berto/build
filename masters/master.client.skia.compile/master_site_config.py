# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""


from common.skia import global_constants
from config_bootstrap import Master


class SkiaCompile(Master.Master3):
  project_name = 'SkiaCompile'
  master_port = 8095
  slave_port = 8195
  master_port_alt = 8295
  repo_url = global_constants.SKIA_REPO
  buildbot_url = 'http://build.chromium.org/p/client.skia.compile/'
  code_review_site = 'https://codereview.chromium.org'
  service_account_file = global_constants.SERVICE_ACCOUNT_FILE
  buildbucket_bucket = 'master.client.compile'
