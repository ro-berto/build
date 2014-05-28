# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import gatekeeper
from master import master_utils

# This is the list of the builder categories and the corresponding critical
# steps. If one critical step fails, gatekeeper will close the tree
# automatically.
# Note: don't include 'update scripts' since we can't do much about it when
# it's failing and the tree is still technically fine.
# Note also: even though the GPU recipe supports adding steps on the
# fly, this list of steps currently must be kept in sync with the
# recipe manually, and the master must be restarted in order to pick
# up changes to this list.
# Note finally: when making changes to which builders are watched in
# slaves.cfg in this directory, also update the list of tree closers
# in 'c.bar_gpu_closers' in
# masters/master.chromium/templates/announce.html .
categories_steps = {
  # We leave the '' category empty because we want to selectively enable
  # the gatekeeper for certain builders, and want to assign categories
  # to specific builders to make them tree closers. Otherwise, the
  # entries in the '' category would close the tree for every builder
  # and tester on the waterfall. Note that the '' category must be present
  # for the gatekeeper logic to activate, see https://crbug.com/378100.
  '': [],

  # We don't specify this category for any of the bots. If any of
  # these steps fail, just ignore them since there's nothing a user's
  # code could have done to affect them.
  'ignored': [
    'update_scripts',
    'setup_build',
    'cleanup temp',
    'gclient setup',
    'gclient revert',
    'gclient sync',
    'git setup (swarming_client)',
    'git fetch (swarming_client)',
    'git checkout (swarming_client)',
    'git clean (swarming_client)',
    'submodule sync (swarming_client)',
    'submodule update (swarming_client)',
    'copy parent_got_revision to got_revision',
    'killall gnome-keyring-daemon',
  ],
  'testers': [
    # These step names were extracted manually from recent builds on a
    # couple of the bots. It's currently necessary to keep them in
    # sync with the recipe.
    # TOOD(kbr): migrate this to gatekeeper-ng when available, and
    # make this automatic.
    'angle_unittests',
    'content_gl_tests',
    'context_lost_tests',
    'gles2_conform_test',
    'gl_tests',
    'gpu_process_launch_tests',
    'gpu_rasterization_tests',
    'hardware_accelerated_feature_tests',
    'maps_pixel_test',
    'memory_test',
    'pixel_test',
    'screenshot_sync_tests',
    'tab_capture_end2end_tests',
    'tab_capture_performance_tests',
    'webgl_conformance_tests',
   ],
  'compile': ['gclient runhooks', 'compile', 'package_build',
              'find isolated tests'],
}

exclusions = {
}

# Note: these steps still close the tree, but they don't email the
# committer, just the sheriff.
forgiving_steps = [
]

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
      tree_status_url=active_master.tree_status_url,
      public_html='../master.chromium/public_html',
      use_getname=True,
      sheriffs=['sheriff_gpu']))
