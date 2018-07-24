# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.status.builder import FAILURE
from master import chromium_notifier
from master import master_utils


forgiving_steps = ['update_scripts', 'update', 'svnkill', 'taskkill',
                   'gclient_revert']

vtunejit_categories_steps = {'vtunejit': ['runhooks', 'compile']}

class V8Notifier(chromium_notifier.ChromiumNotifier):
  def isInterestingStep(self, build_status, step_status, results):
    """Watch only failing steps."""
    return results[0] == FAILURE


def Update(config, active_master, c):
  c['status'].append(V8Notifier(
      fromaddr=active_master.from_address,
      categories_steps=vtunejit_categories_steps,
      exclusions={},
      relayhost=config.Master.smtp,
      sendToInterestedUsers=False,
      extraRecipients=['chunyang.dai@intel.com'],
      status_header='buildbot failure in %(project)s on %(builder)s, %(steps)s',
      lookup=master_utils.FilterDomain(),
      forgiving_steps=forgiving_steps))
