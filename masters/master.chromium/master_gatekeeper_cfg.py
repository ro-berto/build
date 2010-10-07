 # Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import build_utils
from master import gatekeeper
from master import master_config
from master import master_utils

# This is the list of the builder categories and the corresponding critical
# steps. If one critical step fails, gatekeeper will close the tree
# automatically.
# Note: don't include 'update scripts' since we can't do much about it when
# it's failing and the tree is still technically fine.
categories_steps = {
  '': ['update'],
  'testers': [
    'Start Crash Handler',
    'sizes',
    # Unit tests
    'app_unittests',
    'base_unittests',
    #'browser_tests',
    'courgette_unittests',
    'googleurl_unittests',
    #'interactive_ui_tests',
    'ipc_tests',
    'installer_util_unittests',
    'media_unittests',
    'mini_installer_test',
    'net_unittests',
    'plugin_tests',
    'printing_unittests',
    'remoting_unittests',
    'sbox_unittests',
    'sbox_integration_tests',
    'sbox_validation_tests',
    'selenium_tests',
    'test_shell_tests',
    'unit_tests',
    #'ui_tests',
    #'webkit_tests',
   ],
  'windows': ['svnkill', 'taskkill'],
  'compile': ['check deps', 'compile', 'archived build']
}

exclusions = {
    'Chromium Arm': None,
    'Chromium Arm (dbg)': None,
}

forgiving_steps = ['update scripts', 'update', 'svnkill', 'taskkill',
                   'archived build', 'Start Crash Handler']

def Update(config, active_master, c):
  c['status'].append(gatekeeper.GateKeeper(
      fromaddr=active_master.from_address,
      categories_steps=categories_steps,
      exclusions=exclusions,
      relayhost=config.Master.smtp,
      subject='buildbot %(result)s in %(projectName)s on %(builder)s, '
              'revision %(revision)s',
      extraRecipients=active_master.tree_closing_notification_recipients,
      lookup=master_utils.FilterDomain(),
      forgiving_steps=forgiving_steps,
      tree_status_url=active_master.tree_status_url))