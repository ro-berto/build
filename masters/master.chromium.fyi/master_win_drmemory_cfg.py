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

win = lambda: chromium_factory.ChromiumFactory('src/out', 'win32')

defaults['category'] = 'drmemory'

#
# Main Dr. Memory release scheduler for src/
#
S('chromium_drmemory_lkgr', branch='lkgr')

#
# Windows LKGR DrMemory Builder
#
B('Windows LKGR (DrMemory)', 'win_lkgr_drmemory',
  # not use a gatekeeper yet
  scheduler='chromium_drmemory_lkgr',
  notify_on_missing=True)
F('win_lkgr_drmemory', win().ChromiumFactory(
    clobber=True,
    slave_type='Builder',
    options=['--build-tool=ninja', '--', 'chromium_builder_dbg_drmemory_win'],
    compile_timeout=9600, # Release build is LONG
    factory_properties={
      'package_pdb_files': True,
      'gclient_env': {
        'GYP_DEFINES': ('build_for_tool=drmemory '
                        'component=shared_library '),
        'GYP_GENERATORS': 'ninja',
      },
      'cf_archive_build': ActiveMaster.is_production_host,
      'cf_archive_name': 'drmemory',
      'gs_acl': 'public-read',
      'gs_bucket': 'gs://chromium-browser-drfuzz/chromium_win32',
    }))

#
# Windows LKGR DrMemory X64 Builder
#
B('Windows LKGR (DrMemory x64)', 'win_lkgr_drmemory_x64',
  # not use a gatekeeper yet
  scheduler='chromium_drmemory_lkgr',
  notify_on_missing=True)
F('win_lkgr_drmemory_x64', win().ChromiumFactory(
    clobber=True,
    slave_type='Builder',
    target='Release_x64',
    options=['--build-tool=ninja', '--', 'chromium_builder_dbg_drmemory_win'],
    compile_timeout=9600, # Release build is LONG
    factory_properties={
      'package_pdb_files': True,
      'gclient_env': {
        'GYP_DEFINES': ('build_for_tool=drmemory '
                        'component=shared_library '
                        'target_arch=x64'),
        'GYP_GENERATORS': 'ninja',
      },
      'late_cf_archive_build': ActiveMaster.is_production_host,
      'cf_archive_name': 'drmemory_x64',
      'gs_acl': 'public-read',
      'gs_bucket': 'gs://chromium-browser-drfuzz/chromium_win64',
    }))

def Update(_update_config, _active_master, c):
  return helper.Update(c)
