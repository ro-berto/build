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
    'test_suite': 'more_configs',
  },
  'webrtc_android': {
    'chromium_config': 'android',
    'gclient_config': 'webrtc',
    'gclient_apply_config': ['android'],
    'test_suite': 'more_configs',
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
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'cpu': 'x86-64',
        },
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
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86-64',
        },
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
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'cpu': 'x86-64',
        },
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
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86-64',
        },
      },
    },
  },
})


def RunSteps(api):
  webrtc = api.webrtc
  webrtc.apply_bot_config(BUILDERS, RECIPE_CONFIGS)

  webrtc.configure_swarming()

  webrtc.checkout()

  api.chromium.ensure_goma()
  api.chromium.runhooks()

  phases = ['intelligibility_enhancer_no_include_tests',
            'bwe_test_logging',
            'dummy_audio_file_devices_no_protobuf',
            'rtti_no_sctp']
  for phase in phases:
    webrtc.configure_isolate(phase)
    webrtc.compile(phase)

    if webrtc.should_test:
      webrtc.runtests(phase)


def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield test
