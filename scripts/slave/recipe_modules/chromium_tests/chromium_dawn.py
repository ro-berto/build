# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

def CreateBuilderConfig(os, bits, top_of_tree):
  return {
    'chromium_config': 'chromium',
    'chromium_apply_config': [
        'mb',
    ],
    'gclient_config': 'chromium',
    'gclient_apply_config': ['dawn_top_of_tree'] if top_of_tree else [],
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': bits,
    },
    'bot_type': 'builder',
    'testing': {
      'platform': os,
    },
    'checkout_dir': os,
  }

def CreateTesterConfig(os, bits, builder):
  return {
    'chromium_config': 'chromium',
    'chromium_apply_config': [
      'mb',
    ],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': bits,
    },
    'bot_type': 'tester',
    'parent_buildername': builder,
    'testing': {
      'platform': os,
    },
    'serialize_tests': True,
  }

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-dawn-archive',
  },
  'builders': {
    'Dawn Linux x64 Builder':
    CreateBuilderConfig('linux', 64, top_of_tree=True),

    'Dawn Linux x64 Release (Intel HD 630)':
    CreateTesterConfig('linux', 64, 'Dawn Linux x64 Builder'),

    'Dawn Linux x64 Release (NVIDIA)':
    CreateTesterConfig('linux', 64, 'Dawn Linux x64 Builder'),

    'Dawn Linux x64 DEPS Builder':
    CreateBuilderConfig('linux', 64, top_of_tree=False),

    'Dawn Linux x64 DEPS Release (Intel HD 630)':
    CreateTesterConfig('linux', 64, 'Dawn Linux x64 DEPS Builder'),

    'Dawn Linux x64 DEPS Release (NVIDIA)':
    CreateTesterConfig('linux', 64, 'Dawn Linux x64 DEPS Builder'),

    'Dawn Mac x64 Builder':
    CreateBuilderConfig('mac', 64, top_of_tree=True),

    # This bot is actually running on a thin Linux VM. Currently attempting to
    # make it possible to use Linux VMs for all of the testers.
    'Dawn Mac x64 Release (AMD)':
    CreateTesterConfig('mac', 64, 'Dawn Mac x64 Builder'),

    'Dawn Win10 x86 Builder':
    CreateBuilderConfig('win', 32, top_of_tree=True),

    'Dawn Win10 x64 Builder':
    CreateBuilderConfig('win', 64, top_of_tree=True),

    'Dawn Win10 x86 Release (Intel HD 630)':
    CreateTesterConfig('win', 32, 'Dawn Win10 x86 Builder'),

    'Dawn Win10 x64 Release (Intel HD 630)':
    CreateTesterConfig('win', 64, 'Dawn Win10 x64 Builder'),

    'Dawn Win10 x86 Release (NVIDIA)':
    CreateTesterConfig('win', 32, 'Dawn Win10 x86 Builder'),

    'Dawn Win10 x64 Release (NVIDIA)':
    CreateTesterConfig('win', 64, 'Dawn Win10 x64 Builder'),

    'Dawn Win10 x86 DEPS Builder':
    CreateBuilderConfig('win', 32, top_of_tree=False),

    'Dawn Win10 x64 DEPS Builder':
    CreateBuilderConfig('win', 64, top_of_tree=False),

    'Dawn Win10 x86 DEPS Release (Intel HD 630)':
    CreateTesterConfig('win', 32, 'Dawn Win10 x86 DEPS Builder'),

    'Dawn Win10 x64 DEPS Release (Intel HD 630)':
    CreateTesterConfig('win', 64, 'Dawn Win10 x64 DEPS Builder'),

    'Dawn Win10 x86 DEPS Release (NVIDIA)':
    CreateTesterConfig('win', 32, 'Dawn Win10 x86 DEPS Builder'),

    'Dawn Win10 x64 DEPS Release (NVIDIA)':
    CreateTesterConfig('win', 64, 'Dawn Win10 x64 DEPS Builder'),
  },
}
