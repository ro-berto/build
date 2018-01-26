# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze


DEPS = [
  'depot_tools/bot_update',
  'chromium',
  'recipe_engine/step',
  'webrtc',
]

RECIPE_CONFIGS = freeze({
  'webrtc_default': {
    'chromium_config': 'webrtc_default',
    'gclient_config': 'webrtc',
  },
  'webrtc_android': {
    'chromium_config': 'android',
    'gclient_config': 'webrtc',
    'gclient_apply_config': ['android'],
  },
})

BUILDERS = freeze({
  'client.webrtc': {
    'builders': {
      'Linux (more configs)': {
        'recipe_config': 'webrtc_default',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'Android32 (more configs)': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'Win (more configs)': {
        'recipe_config': 'webrtc_default',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
    },
  },
  'tryserver.webrtc': {
    'builders': {
      'linux_more_configs': {
        'recipe_config': 'webrtc_default',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'android_more_configs': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'win_more_configs': {
        'recipe_config': 'webrtc_default',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
    },
  },
})


def BuildSteps(api, name, *gn_args):
  api.chromium.c.build_config_fs = name
  api.chromium.c.gn_args = list(gn_args)
  api.chromium.run_gn(use_goma=True)
  api.step.active_result.presentation.step_text = 'gn (%s)' % (name)
  api.chromium.compile(use_goma_module=True)


def RunSteps(api):
  api.webrtc.apply_bot_config(BUILDERS, RECIPE_CONFIGS)

  api.webrtc.checkout()
  api.chromium.ensure_goma()
  api.chromium.runhooks()

  BuildSteps(api, 'minimal')
  BuildSteps(api, 'intelligibility_enhancer',
             'rtc_enable_intelligibility_enhancer=true')
  BuildSteps(api, 'no_include_tests', 'rtc_include_tests=false')
  BuildSteps(api, 'no_protobuf', 'rtc_enable_protobuf=false')
  BuildSteps(api, 'bwe_test_logging', 'rtc_enable_bwe_test_logging=true')
  if api.chromium.c.TARGET_PLATFORM != 'android':
    # Sanity check for the rtc_enable_bwe_test_logging=true build.
    api.webrtc.run_baremetal_test('bwe_simulations_tests',
        gtest_args=['--gtest_filter=VideoSendersTest/'
                    'BweSimulation.Choke1000kbps500kbps1000kbps/1'])
  BuildSteps(api, 'dummy_audio_file_devices',
             'rtc_use_dummy_audio_file_devices=true')
  BuildSteps(api, 'rtti', 'use_rtti=true')
  BuildSteps(api, 'no_sctp', 'rtc_enable_sctp=false')
  if api.chromium.c.TARGET_PLATFORM != 'android':
    # Sanity check for the rtc_enable_sctp=false build.
    api.webrtc.run_baremetal_test('peerconnection_unittests')


def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield test
