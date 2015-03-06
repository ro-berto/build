# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master import master_utils
from master.factory import chromium_factory

import master_site_config
ActiveMaster = master_site_config.ChromiumFYI

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler
T = helper.Triggerable
U = helper.URLScheduler

win = lambda: chromium_factory.ChromiumFactory('src/out', 'win32')

defaults['category'] = 'drmemory'

#
# Main Dr. Memory release scheduler for src/
#
S('win_lkgr_drmemory', branch='master', treeStableTimer=60)

#
# Windows LKGR DrMemory Builder
#
U('CR-LKGR', 'https://chromium-status.appspot.com/lkgr', include_revision=True)
B('Windows LKGR (DrMemory)', 'win_lkgr_drmemory', 'lkgr', 'CR-LKGR',
  notify_on_missing=True)
F('win_lkgr_drmemory', win().ChromiumFactory(
    clobber=True,
    slave_type='BuilderTester',
    options=['--build-tool=ninja', '--', 'chromium_builder_lkgr_drmemory_win'],
    compile_timeout=7200,
    tests=[
      'drmemory_light_webkit',
      'drmemory_full_webkit',
    ],
    factory_properties={
      'package_pdb_files': True,
      'gclient_env': {
        'GYP_DEFINES': ('build_for_tool=drmemory '
                        'component=shared_library '),
        'GYP_GENERATORS': 'ninja',
      },
      'late_cf_archive_build': ActiveMaster.is_production_host,
      'cf_archive_name': 'drmemory',
      'gs_acl': 'public-read',
      'gs_bucket': 'gs://chromium-browser-drmemory',
    }))

def Update(_update_config, _active_master, c):
  return helper.Update(c)
