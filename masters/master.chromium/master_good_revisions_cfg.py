# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import goodrevisions

# This is the list of builders with their respective list of critical steps
# that all need to succeed to mark a revision as successful. A single failure
# in any of the steps of any of the builders will mark the revision as failed.
good_revision_steps = {
  # Dependent on 'Win Builder (dbg)'
  'Vista Tests (dbg)(1)': [
    'check_deps', 'base_unittests', 'courgette_unittests',
    'googleurl_unittests', 'media_unittests', 'printing_unittests',
    'remoting_unittests', 'ipc_tests', 'sync_unit_tests', 'unit_tests',
    'app_unittests', 'installer_util_unittests', 'gfx_unittests',
    'crypto_unittests',
  ],
  'Vista Tests (dbg)(2)': [
    'net_unittests', 'ui_tests', 'browser_tests',
  ],
  'Vista Tests (dbg)(3)': [
    'ui_tests', 'browser_tests',
  ],
  'Vista Tests (dbg)(4)': [
    'ui_tests', 'browser_tests',
  ],
  'Vista Tests (dbg)(5)': [
    'ui_tests', 'browser_tests',
  ],
  'Interactive Tests (dbg)': [
    'interactive_ui_tests',
  ],
  # Dependent on 'Mac Builder (dbg)'
  'Mac 10.5 Tests (dbg)(1)': [
    'check_deps', 'base_unittests', 'googleurl_unittests', 'media_unittests',
    'printing_unittests', 'remoting_unittests', 'ipc_tests', 'sync_unit_tests',
    'unit_tests', 'app_unittests', 'interactive_ui_tests', 'gfx_unittests',
  ],
  'Mac 10.5 Tests (dbg)(2)': [
    'net_unittests', 'ui_tests',
  ],
  'Mac 10.5 Tests (dbg)(3)': [
    'browser_tests',
  ],
  # Dependent on 'Linux Builder (dbg)'
  'Linux Tests (dbg)(1)': [
    'check_deps',  'browser_tests', 'net_unittests',
  ],
  'Linux Tests (dbg)(2)': [
    'ui_tests', 'ipc_tests', 'sync_unit_tests', 'unit_tests',
    'app_unittests', 'interactive_ui_tests', 'base_unittests',
    'googleurl_unittests', 'media_unittests', 'printing_unittests',
    'remoting_unittests', 'gfx_unittests',
  ],
  'Linux Builder (ChromiumOS)': [
    'compile',
    'base_unittests', 'googleurl_unittests', 'media_unittests',
    'net_unittests', 'printing_unittests', 'remoting_unittests',
    'ipc_tests', 'sync_unit_tests', 'unit_tests', 'app_unittests',
    'gfx_unittests',
  ],
  # Disabled - It takes an hour to cycle.
  #'Linux Builder (ChromiumOS dbg)': [
  #  'compile',
  #  'base_unittests', 'googleurl_unittests', 'media_unittests',
  #  'net_unittests', 'printing_unittests', 'remoting_unittests',
  #  'ipc_tests', 'sync_unit_tests', 'unit_tests', 'app_unittests',
  #],
}

def Update(config, active_master, c):
  c['status'].append(goodrevisions.GoodRevisions(
      good_revision_steps=good_revision_steps,
      store_revisions_url=active_master.store_revisions_url))
