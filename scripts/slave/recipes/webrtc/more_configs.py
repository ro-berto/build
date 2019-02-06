# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import functools

from recipe_engine.types import freeze


DEPS = [
  'depot_tools/bot_update',
  'chromium',
  'recipe_engine/properties',
  'recipe_engine/runtime',
  'recipe_engine/step',
  'webrtc',
]

RECIPE_CONFIGS = freeze({
  'webrtc': {
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
  'luci.webrtc.ci': {
    'settings': {
      'mastername': 'client.webrtc',
    },
    'builders': {
      'Linux (more configs)': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
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
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86-64',
        },
      },
    },
  },
  'luci.webrtc.try': {
    'settings': {
      'mastername': 'tryserver.webrtc',
    },
    'builders': {
      'linux_more_configs': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'cpu': 'x86-64',
        },
      },
      'android_arm_more_configs': {
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
      'win_x86_more_configs': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
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

  phases = ['bwe_test_logging',
            'dummy_audio_file_devices_no_protobuf',
            'rtti_no_sctp']
  for phase in phases:
    webrtc.configure_isolate(phase)
    webrtc.run_mb(phase)
    webrtc.compile(phase)

    if webrtc.bot.should_test:
      webrtc.runtests(phase)


def GenTests(api):
  builders = BUILDERS
  generate_builder = functools.partial(api.webrtc.generate_builder, builders)

  for bucketname in builders.keys():
    master_config = builders[bucketname]
    for buildername in master_config['builders'].keys():
      yield generate_builder(bucketname, buildername, revision='a' * 40)
