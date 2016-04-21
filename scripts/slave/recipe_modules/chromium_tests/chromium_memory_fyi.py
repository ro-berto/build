# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-memory-fyi-archive',
  },
  'builders': {
    'Chromium Linux MSan Builder': {
      'chromium_config': 'chromium_msan',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['mb', 'prebuilt_instrumented_libraries'],
      'GYP_DEFINES': {
        'msan_track_origins': 2,
      },
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {'platform': 'linux'},
      'enable_swarming': True,
      'use_isolate': True,
    },
    'Linux MSan Tests': {
      'chromium_config': 'chromium_msan',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'parent_buildername': 'Chromium Linux MSan Builder',
      'testing': {'platform': 'linux'},
      'enable_swarming': True,
    },
    'Chromium Linux ChromeOS MSan Builder': {
      'chromium_config': 'chromium_msan',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['mb', 'prebuilt_instrumented_libraries'],
      'GYP_DEFINES': {
        'msan_track_origins': 2,
        'chromeos': 1
      },
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {'platform': 'linux'},
      'enable_swarming': True,
      'use_isolate': True,
    },
    'Linux ChromeOS MSan Tests': {
      'chromium_config': 'chromium_msan',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'parent_buildername': 'Chromium Linux ChromeOS MSan Builder',
      'testing': {'platform': 'linux'},
      'enable_swarming': True,
    },
    'Chromium Linux TSan Builder': {
      'chromium_config': 'chromium_tsan2',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
      'use_isolate': True,
    },
    'Linux TSan Tests': {
      'chromium_config': 'chromium_tsan2',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'parent_buildername': 'Chromium Linux TSan Builder',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'Chromium Linux Builder (valgrind)': {
      'compile_targets': [
        'base_unittests',
        'components_unittests',
        'content_unittests',
        'crypto_unittests',
        'device_unittests',
        'display_unittests',
        'extensions_unittests',
        'gcm_unit_tests',
        'gpu_unittests',
        'ipc_tests',
        'jingle_unittests',
        'media_unittests',
        'midi_unittests',
        'net_unittests',
        'ppapi_unittests',
        'printing_unittests',
        'remoting_unittests',
        'sandbox_linux_unittests',
        'sql_unittests',
        'sync_unit_tests',
        'ui_base_unittests',
        'unit_tests',
        'url_unittests',
      ],
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['mb', 'memcheck'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },
  },
}

def BaseSpec(bot_type, chromium_apply_config, gclient_apply_config):
  spec = {
    'bot_type': bot_type,
    'chromium_apply_config' : chromium_apply_config,
    'chromium_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': 64,
    },
    'gclient_config': 'chromium',
    'gclient_apply_config': gclient_apply_config,
    'testing': {
      'platform': 'linux',
    },
  }
  return spec

def TestSpec(parent_builder):
  spec = BaseSpec(
    bot_type='tester',
    chromium_apply_config=['mb'],
    gclient_apply_config=['valgrind'])

  spec['parent_buildername'] = parent_builder
  spec['test_generators'] = [
    steps.generate_gtest,
    steps.generate_script,
    steps.generate_isolated_script,
  ]
  return spec

def AddMemTestSpec(name, tool):
  if tool == 'valgrind':
    SPEC['builders'][name] = TestSpec('Chromium Linux Builder (valgrind)')

AddMemTestSpec('Linux Tests (valgrind)(1)', 'valgrind')
AddMemTestSpec('Linux Tests (valgrind)(2)', 'valgrind')
AddMemTestSpec('Linux Tests (valgrind)(3)', 'valgrind')
AddMemTestSpec('Linux Tests (valgrind)(4)', 'valgrind')
AddMemTestSpec('Linux Tests (valgrind)(5)', 'valgrind')
