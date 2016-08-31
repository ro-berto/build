# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class ChromiumPerfFyi(Master.Master1):
  project_name = 'Chromium Perf Fyi'
  master_port = 8061
  slave_port = 8161
  master_port_alt = 8261
  buildbot_url = 'http://build.chromium.org/p/chromium.perf.fyi/'
  service_account_file = 'service-account-chromium.json'

  # master.chromium.perf.fyi uses bulidbucket in an interesting way:
  #
  # master.chromium.perf has builders and testers, but master.chromium.perf.fyi
  # has only testers. The former builds chromium and triggers testers on the FYI
  #
  # Some builders on master.chromium.perf run for each commit, and thus trigger
  # builds on FYI for each commit. FYI does not have capacity to run a build
  # for each commit, so it uses buildbot "merge requests" feature that collapses
  # multiple build requests into a single build.
  #
  # The chromium.perf -> chromium.perf.fyi build triggering is implemented using
  # buildbucket which does not support build request merging. As a result,
  # buildbucket builds are converted to buildbot build requests, one buildbot
  # build is run (with a proper blamelist) and then, due to the issue,
  # only one buildbucket build is updated with the build result and the rest
  # are marked cancelled.
  #
  # However, nothing consumes buildbucket build results, including the builds
  # that trigger them. Only humans care about the triggered builds and they
  # consume them by looking at the buildbot pages which don't have the issue,
  # because the build requests are correctly scheduled, and the build with a
  # correct blamelist is run. So, this is fine.
  buildbucket_bucket = 'master.chromium.perf.fyi'
  # Buildbucket creates a "changes" table row for each change in each
  # buildbucket build (unless global change id is specified; it is not), and
  # buildbot console view does not like it. We can it avoid by telling
  # buildbucket that all changes have unique URLs (because they are chromium
  # commit URLs, see long comment above), so buildbucket reuses "changes" table
  # rows created by gitiles poller.
  buildbucket_unique_change_urls = True
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'chromium.perf.fyi'
