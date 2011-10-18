# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import gatekeeper
from master import master_utils

# This is the list of the builder categories and the corresponding critical
# steps. If one critical step fails, gatekeeper will close the tree
# automatically.
# Note: don't include 'update scripts' since we can't do much about it when
# it's failing and the tree is still technically fine.
chromium_categories_steps = {
  '': ['update'],
  'testers': [
    'start_crash_handler',
    'sizes',
    # Unit tests
    'base_unittests',
    #'browser_tests',
    'cacheinvalidation_unittests',
    'content_unittests',
    'courgette_unittests',
    'crypto_unittests',
    'googleurl_unittests',
    #'interactive_ui_tests',
    'ipc_tests',
    'installer_util_unittests',
    'jingle_unittests',
    'media_unittests',
    'mini_installer_test',
    'nacl_integration',
    'net_unittests',
    'plugin_tests',
    'printing_unittests',
    'remoting_unittests',
    'sbox_unittests',
    'sbox_integration_tests',
    'sbox_validation_tests',
    'sql_unittests',
    'test_shell_tests',
    'unit_tests',
    #'ui_tests',
    #'webkit_tests',
   ],
  'compile': ['check_deps', 'compile', 'archive_build'],
  'closer': ['BuildTarget'],
}

exclusions = {
}

forgiving_steps = ['update_scripts', 'update', 'svnkill', 'taskkill',
                   'archive_build', 'start_crash_handler']

close_chromiumos_categories_steps = {
  'closer': [
    'LKGMSync',
    'BuildBoard',
    'BuildTarget',
    'UnitTest',
  ],
}

warn_chromiumos_categories_steps = {
  'watch': [
    'LKGMSync',
    'UploadPrebuilts',
    'Archive',
  ],
}

subject = ('buildbot %(result)s in %(projectName)s on %(builder)s, '
           'revision %(revision)s')

def Update(config, active_master, alternate_master, c):
  c['status'].append(gatekeeper.GateKeeper(
      fromaddr=active_master.from_address,
      categories_steps=chromium_categories_steps,
      exclusions=exclusions,
      relayhost=config.Master.smtp,
      subject=subject,
      extraRecipients=active_master.tree_closing_notification_recipients,
      lookup=master_utils.FilterDomain(),
      forgiving_steps=forgiving_steps,
      tree_status_url=active_master.tree_status_url,
      sheriffs=['sheriff'],
      use_getname=True))
  c['status'].append(gatekeeper.GateKeeper(
      fromaddr=active_master.from_address,
      categories_steps=close_chromiumos_categories_steps,
      exclusions=exclusions,
      relayhost=config.Master.smtp,
      subject='Closer ' + subject,
      extraRecipients=alternate_master.tree_closing_notification_recipients,
      lookup=master_utils.FilterDomain(),
      forgiving_steps=forgiving_steps,
      tree_status_url=alternate_master.tree_status_url,
      sheriffs=['sheriff_cros_mtv', 'sheriff_cros_nonmtv'],
      use_getname=True))
  c['status'].append(gatekeeper.GateKeeper(
      fromaddr=active_master.from_address,
      categories_steps=warn_chromiumos_categories_steps,
      exclusions=exclusions,
      relayhost=config.Master.smtp,
      subject='Warning ' + subject,
      extraRecipients=alternate_master.tree_closing_notification_recipients,
      lookup=master_utils.FilterDomain(),
      forgiving_steps=forgiving_steps,
      tree_status_url=None,
      sheriffs=['sheriff_cros_mtv', 'sheriff_cros_nonmtv'],
      use_getname=True))
