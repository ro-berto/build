# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import goodrevisions

# This is the list of builders with their respective list of critical steps
# that all need to succeed to mark a revision as successful. A single failure
# in any of the steps of any of the builders will mark the revision as failed.
good_revision_steps = {
  # Dependent on 'Chromium Builder (dbg)'
  'XP Tests (dbg)(1)': [
    'check deps', 'courgette_unittests', 'googleurl_unittests',
    'media_unittests', 'printing_unittests', 'remoting_unittests',
    'ipc_tests', 'sync_unit_tests', 'unit_tests', 'app_unittests',
    'installer_util_unittests',
  ],
  'XP Tests (dbg)(2)': [
    'ui_tests',
  ],
  'XP Tests (dbg)(3)': [
    'ui_tests',
  ],
  'XP Tests (dbg)(4)': [
    'ui_tests', 'browser_tests',
  ],
  'Modules XP (dbg)': [
    'base_unittests', 'net_unittests',
  ],
  'Interactive Tests (dbg)': [
    'interactive_ui_tests',
  ],
  # Dependent on 'Chromium Mac Builder (dbg)'
  'Mac10.5 Tests (dbg)(1)': [
    'check deps', 'googleurl_unittests', 'media_unittests',
    'printing_unittests', 'remoting_unittests',
    'ipc_tests', 'sync_unit_tests', 'unit_tests', 'app_unittests',
    'interactive_ui_tests',
  ],
  'Mac10.5 Tests (dbg)(2)': [
    'ui_tests',
  ],
  'Mac10.5 Tests (dbg)(3)': [
    'browser_tests',
  ],
  'Modules Mac10.5 (dbg)': [
    'base_unittests', 'net_unittests',
  ],
  # Dependent on 'Chromium Linux Builder (dbg)'
  'Linux Tests (dbg)(1)': [
    'check deps', 'googleurl_unittests', 'media_unittests',
    'printing_unittests', 'remoting_unittests', 'browser_tests', 'ui_tests',
  ],
  'Linux Tests (dbg)(2)': [
    'ipc_tests', 'sync_unit_tests', 'unit_tests', 'app_unittests', 'ui_tests',
    'interactive_ui_tests',
  ],
  'Modules Linux (dbg)': [
    'base_unittests', 'net_unittests',
  ],
  'Linux Builder (ChromiumOS)': [
    'compile',
    'base_unittests', 'googleurl_unittests', 'media_unittests',
    'net_unittests', 'printing_unittests', 'remoting_unittests',
    'ipc_tests', 'sync_unit_tests', 'unit_tests', 'app_unittests',
  ],
  'Linux Builder (ChromiumOS dbg)': [
    'compile',
    'base_unittests', 'googleurl_unittests', 'media_unittests',
    'net_unittests', 'printing_unittests', 'remoting_unittests',
    'ipc_tests', 'sync_unit_tests', 'unit_tests', 'app_unittests',
  ],
}

def Update(config, active_master, c):
  c['status'].append(goodrevisions.GoodRevisions(
      good_revision_steps=good_revision_steps,
      store_revisions_url=active_master.store_revisions_url))
