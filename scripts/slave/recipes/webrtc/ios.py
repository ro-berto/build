# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import functools

from recipe_engine.types import freeze


DEPS = [
  'depot_tools/bot_update',
  'chromium',
  'ios',
  'recipe_engine/properties',
  'recipe_engine/runtime',
  'recipe_engine/step',
  'webrtc',
]

RECIPE_CONFIGS = freeze({
  'webrtc_ios': {
    'chromium_config': 'webrtc_default',
    'gclient_config': 'webrtc_ios',
    'test_suite': 'ios',
  },
})

BUILDERS = freeze({
  'luci.webrtc.ci': {
    'settings': {
      'mastername': 'client.webrtc',
    },
    'builders': {
      'iOS32 Debug': {
        'recipe_config': 'webrtc_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'ios',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
        'ensure_sdk': 'ios',
        'ios_config': {
          'sdk': 'iphoneos10.3',
        },
      },
      'iOS32 Release': {
        'recipe_config': 'webrtc_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'ios',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
        'ensure_sdk': 'ios',
        'ios_config': {
          'sdk': 'iphoneos10.3',
        },
      },
      'iOS64 Debug': {
        'recipe_config': 'webrtc_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'ios',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
        'ensure_sdk': 'ios',
        'ios_config': {
          'sdk': 'iphoneos10.3',
        },
      },
      'iOS64 Release': {
        'recipe_config': 'webrtc_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'ios',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
        'ensure_sdk': 'ios',
        'ios_config': {
          'sdk': 'iphoneos10.3',
        },
      },
      'iOS64 Sim Debug (iOS 9.0)': {
        'recipe_config': 'webrtc_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'ios',
          'TARGET_ARCH': 'intel',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
        'ensure_sdk': 'ios',
        'ios_config': {
          'sdk': 'iphonesimulator9.3',
        },
        'ios_testing': {
          'device type': 'iPhone 6s',
          'os': '9.3',
          'host os': 'Mac-10.13',
        },
      },
      'iOS64 Sim Debug (iOS 10.0)': {
        'recipe_config': 'webrtc_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'ios',
          'TARGET_ARCH': 'intel',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
        'ensure_sdk': 'ios',
        'ios_config': {
          'sdk': 'iphonesimulator10.3',
        },
        'ios_testing': {
          'device type': 'iPhone 6s',
          'os': '10.3',
          'host os': 'Mac-10.13',
        },
      },
    },
  },
  'luci.webrtc.try': {
    'settings': {
      'mastername': 'tryserver.webrtc',
    },
    'builders': {
      'ios_compile_arm_dbg': {
        'recipe_config': 'webrtc_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'ios',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
        'ensure_sdk': 'ios',
        'ios_config': {
          'sdk': 'iphoneos10.3',
        },
      },
      'ios_compile_arm_rel': {
        'recipe_config': 'webrtc_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'ios',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
        'ensure_sdk': 'ios',
        'ios_config': {
          'sdk': 'iphoneos10.3',
        },
      },
      'ios_compile_arm64_dbg': {
        'recipe_config': 'webrtc_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'ios',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
        'ensure_sdk': 'ios',
        'ios_config': {
          'sdk': 'iphoneos10.3',
        },
      },
      'ios_compile_arm64_rel': {
        'recipe_config': 'webrtc_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'ios',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
        'ensure_sdk': 'ios',
        'ios_config': {
          'sdk': 'iphoneos10.3',
        },
      },
      'ios_sim_x64_dbg_ios9': {
        'recipe_config': 'webrtc_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'ios',
          'TARGET_ARCH': 'intel',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
        'ensure_sdk': 'ios',
        'ios_config': {
          'sdk': 'iphonesimulator9.3',
        },
        'ios_testing': {
          'device type': 'iPhone 6s',
          'os': '9.3',
          'host os': 'Mac-10.13',
        },
      },
      'ios_sim_x64_dbg_ios10': {
        'recipe_config': 'webrtc_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'ios',
          'TARGET_ARCH': 'intel',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
        'ensure_sdk': 'ios',
        'ios_config': {
          'sdk': 'iphonesimulator10.3',
        },
        'ios_testing': {
          'device type': 'iPhone 6s',
          'os': '10.3',
          'host os': 'Mac-10.13',
        },
      },
    },
  },
  'luci.webrtc.fake': {
    'settings': {
      'mastername': 'client.webrtc.fake',
    },
    'builders': {
      'Fake Perf Tester': {
        'recipe_config': 'webrtc_ios',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'ios',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'perf_id': 'webrtc-ios-fake',
        'testing': {'platform': 'mac'},
        'ensure_sdk': 'ios',
        'ios_config': {},
        'ios_testing': {
          'device type': 'iPhone 6s',
          'os': '10.3',
          'host os': 'Mac-10.13',
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

  webrtc.check_swarming_version()
  webrtc.configure_isolate()

  with api.step.nest('apply build config'):
    webrtc.apply_ios_config()

  with webrtc.ensure_sdk():
    webrtc.run_mb_ios()
    webrtc.compile()

  if webrtc.bot.should_test:
    with api.step.nest('isolate'):
      tasks = api.ios.isolate()
    with api.step.nest('trigger'):
      api.ios.trigger(tasks)
    if webrtc.bot.should_upload_perf_results:
      api.ios.collect(tasks, result_callback=webrtc.upload_to_perf_dashboard)
    else:
      api.ios.collect(tasks)


def GenTests(api):
  builders = BUILDERS
  generate_builder = functools.partial(api.webrtc.generate_builder, builders)

  for bucketname in builders.keys():
    master_config = builders[bucketname]
    for buildername in master_config['builders'].keys():
      yield (
          generate_builder(bucketname, buildername, revision='a' * 40) +
          # The version is just a placeholder, don't bother updating it:
          api.properties(**{'$depot_tools/osx_sdk': {'sdk_version': '10l232m'}})
      )
