# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
 'builders': {
   'Chromium Linux Goma Staging': {
     'chromium_config': 'chromium',
     'chromium_apply_config': ['goma_staging', 'clobber', 'mb'],
     'gclient_config': 'chromium',
     'chromium_config_kwargs': {
       'BUILD_CONFIG': 'Release',
       'TARGET_BITS': 64,
     },
     'goma_staging': True,
     'testing': {
       'platform': 'linux',
     },
   },
   'Chromium Mac Goma Staging': {
     'chromium_config': 'chromium',
     'chromium_apply_config': ['goma_staging', 'clobber', 'mb'],
     'gclient_config': 'chromium',
     'chromium_config_kwargs': {
       'BUILD_CONFIG': 'Release',
       'TARGET_BITS': 64,
     },
     'goma_staging': True,
     'testing': {
       'platform': 'mac',
     },
   },
   'CrWinGomaStaging': {
     'chromium_config': 'chromium',
     'chromium_apply_config': ['goma_staging', 'clobber', 'mb'],
     'gclient_config': 'chromium',
     'chromium_config_kwargs': {
       'BUILD_CONFIG': 'Release',
       'TARGET_BITS': 64,
     },
     'goma_staging': True,
     'testing': {
       'platform': 'win',
     },
   },
   'Chromium Linux Goma GCE Staging': {
     'chromium_config': 'chromium',
     'chromium_apply_config': ['goma_gce', 'clobber', 'mb'],
     'gclient_config': 'chromium',
     'chromium_config_kwargs': {
       'BUILD_CONFIG': 'Release',
       'TARGET_BITS': 64,
     },
     'goma_staging': True,
     'testing': {
       'platform': 'linux',
     },
   },
   'Chromium Mac Goma GCE Staging': {
     'chromium_config': 'chromium',
     'chromium_apply_config': ['goma_gce', 'clobber', 'mb'],
     'gclient_config': 'chromium',
     'chromium_config_kwargs': {
       'BUILD_CONFIG': 'Release',
       'TARGET_BITS': 64,
     },
     'goma_staging': True,
     'testing': {
       'platform': 'mac',
     },
   },
   'CrWinClangGomaGCEStaging': {
     'chromium_config': 'chromium',
     'chromium_apply_config': ['goma_gce', 'clobber', 'mb'],
     'gclient_config': 'chromium',
     'chromium_config_kwargs': {
       'BUILD_CONFIG': 'Release',
       'TARGET_BITS': 64,
     },
     'goma_staging': True,
     'testing': {
       'platform': 'win',
     },
   },
   'Chromium Linux Goma RBE Staging (clobber)': {
     'chromium_config': 'chromium',
     # use canary until client ready for RBE is released.
     # TODO(ukai): remove this. crbug.com/831046
     'chromium_apply_config': ['goma_gce', 'goma_canary', 'clobber', 'mb'],
     'gclient_config': 'chromium',
     'chromium_config_kwargs': {
       'BUILD_CONFIG': 'Release',
       'TARGET_BITS': 64,
     },
     'goma_staging': True,
     'testing': {
       'platform': 'linux',
     },
   },
   'Chromium Linux Goma RBE Staging': {
     'chromium_config': 'chromium',
     # use canary until client ready for RBE is released.
     # TODO(ukai): remove this. crbug.com/831046
     'chromium_apply_config': ['goma_gce', 'goma_canary', 'mb'],
     'gclient_config': 'chromium',
     'chromium_config_kwargs': {
       'BUILD_CONFIG': 'Release',
       'TARGET_BITS': 64,
     },
     'goma_staging': True,
     'testing': {
       'platform': 'linux',
     },
   },
   'Chromium Linux Goma RBE Staging (dbg) (clobber)': {
     'chromium_config': 'chromium',
     # use canary until client ready for RBE is released.
     # TODO(ukai): remove this. crbug.com/831046
     'chromium_apply_config': ['goma_gce', 'goma_canary', 'clobber', 'mb'],
     'gclient_config': 'chromium',
     'chromium_config_kwargs': {
       'BUILD_CONFIG': 'Debug',
       'TARGET_BITS': 64,
     },
     'goma_staging': True,
     'testing': {
       'platform': 'linux',
     },
   },
   'Chromium Linux Goma RBE Staging (dbg)': {
     'chromium_config': 'chromium',
     # use canary until client ready for RBE is released.
     # TODO(ukai): remove this. crbug.com/831046
     'chromium_apply_config': ['goma_gce', 'goma_canary', 'mb'],
     'gclient_config': 'chromium',
     'chromium_config_kwargs': {
       'BUILD_CONFIG': 'Debug',
       'TARGET_BITS': 64,
     },
     'goma_staging': True,
     'testing': {
       'platform': 'linux',
     },
   },
 },
}
