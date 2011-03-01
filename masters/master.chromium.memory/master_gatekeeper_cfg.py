 # Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import gatekeeper
from master import master_utils

# This is the list of the builder categories and the corresponding critical
# steps. If one critical step fails, gatekeeper will close the tree
# automatically.
# Note: don't include 'update scripts' since we can't do much about it when
# it's failing and the tree is still technically fine.
categories_steps = {
  '': ['update'],
  'memory_tester': [
    'Start Crash Handler',
    'memory test: googleurl',
    'memory test: printing',
    'memory test: media',
    'memory test: remoting',
    'memory test: app',
    'memory test: sync_unit_tests',
    'memory test: ipc',
    'memory test: base',
    'memory test: net',
    'memory test: gfx',
    'memory test: unit',
    'memory test: unit_1',  # it's sharded on Mac Valgrind and TSan Linux
   ],
  'memory_ui_tester': [
    # UI tests are flaky on the Mac Valgrind bots (http://crbug.com/51716),
    # so we watch for UI tests only on Linux and CrOS.
    # TODO(timurrrr): merge this with memory_tester when the issue is resolved.
    'memory test: ui',
    'memory test: ui_1',  # sharded too.
  ],
  'heapcheck_tester': [
    'heapcheck test: googleurl',
    'heapcheck test: printing',
    'heapcheck test: media',
    'heapcheck test: courgette',
    'heapcheck test: remoting',
    'heapcheck test: app',
    'heapcheck test: sync_unit_tests',
    'heapcheck test: ipc',
    'heapcheck test: base',
    'heapcheck test: net',
    'heapcheck test: gfx',
    'heapcheck test: unit',
    'heapcheck test: test_shell',
  ],
  'windows': ['svnkill', 'taskkill'],
  'compile': ['check deps', 'compile', 'archived build']
}

exclusions = {
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
      tree_status_url=None,
      use_getname=True,
      status_header='Failure notification for "%(steps)s" on "%(builder)s".\n'
          'Please see if the failures are related to your commit and take '
          'appropriate actions (e.g. revert, update suppressions, notify '
          'sheriff, etc.).\n\n'
          'For more info on the memory waterfall please see these links:\n'
          'http://dev.chromium.org/developers/how-tos/using-valgrind\n'
          'http://dev.chromium.org/developers/tree-sheriffs/sheriff-details-chromium/memory-sheriff'
          '\n\nBy the way, the current memory sheriff is on the CC list.'
      ))
