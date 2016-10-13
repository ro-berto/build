# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import failures_notifier
from master import master_utils

# This is the list of the builder categories and the corresponding critical
# steps. If one critical step fails, gatekeeper will close the tree
# automatically.
# Note: don't include 'update scripts' since we can't do much about it when
# it's failing and the tree is still technically fine.
categories_steps = {
  '': ['update'],
  'memory_tester': [
    # Please keep the list below sorted.
    'memory test: app_list',
    'memory test: ash_unittests',
    'memory test: aura',
    'memory test: base_unittests',
    'memory test: chromeos_unittests',
    'memory test: components',
    'memory test: compositor',
    'memory test: content',
    'memory test: courgette',
    'memory test: crypto',
    'memory test: device_unittests',
    'memory test: display_unittests',
    'memory test: extensions_unittests',
    'memory test: gpu',
    'memory test: jingle',
    'memory test: ipc_tests',
    'memory test: media',
    'memory test: message_center',
    'memory test: net',
    'memory test: printing',
    'memory test: ppapi_unittests',
    'memory test: remoting',
    'memory test: reliability',
    # Running two times with different tools on the same bot, hence _1 version.
    'memory test: reliability_1',
    'memory test: sandbox',
    'memory test: sql',
    'memory test: sync',
    'memory test: ui_base_unittests',
    'memory test: unit',
    'memory test: unit_1',  # it's sharded on TSan Linux
    'memory test: url',
    'memory test: views',
   ],
  'windows': ['svnkill', 'taskkill'],
  'compile': ['check_deps', 'compile', 'archive_build']
}

exclusions = {
}

forgiving_steps = ['update_scripts', 'update', 'svnkill', 'taskkill',
                   'archive_build']

def Update(config, active_master, c):
  c['status'].append(failures_notifier.FailuresNotifier(
      fromaddr=active_master.from_address,
      categories_steps=categories_steps,
      exclusions=exclusions,
      relayhost=config.Master.smtp,
      subject='buildbot %(result)s in %(projectName)s on %(builder)s, '
              'revision %(revision)s',
      extraRecipients=active_master.tree_closing_notification_recipients,
      lookup=master_utils.FilterDomain(),
      forgiving_steps=forgiving_steps,
      use_getname=True,
      public_html='../master.chromium/public_html',
      sheriffs=['sheriff_memory'],
      status_header='Failure notification for "%(steps)s" on "%(builder)s".\n'
          'Please see if the failures are related to your commit and take '
          'appropriate actions (e.g. revert, update suppressions, notify '
          'sheriff, etc.).\n\n'
          'For more info on the memory waterfall please see these links:\n'
          'http://dev.chromium.org/developers/tree-sheriffs/sheriff-details-chromium/memory-sheriff\n'
          'http://dev.chromium.org/developers/how-tos/using-valgrind/threadsanitizer\n'
          '\nBy the way, the current memory sheriff is on the CC list.'
      ))
