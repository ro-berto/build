# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

RESULTS_URL = 'https://chromeperf.appspot.com'


SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-android-archive',
    # WARNING: src-side runtest.py is only tested with chromium CQ builders.
    # Usage not covered by chromium CQ is not supported and can break
    # without notice.
    'src_side_runtest_py': True,
  },
  'builders': {
    'Android arm Builder (dbg)': {
      'chromium_config': 'android',
      'chromium_apply_config': [
        'download_vr_test_apks',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder_mb',
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },

    'Android arm64 Builder (dbg)': {
      'chromium_config': 'android',
      'chromium_apply_config': [
        'download_vr_test_apks',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder_mb',
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },

    'Android ASAN (dbg)': {
      'chromium_config': 'android_clang',
      'chromium_apply_config': [
          'errorprone',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'clang_builder_mb',
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
    },

    # TODO(jbudorick): Remove this and use android-cronet-arm-rel as the
    # trybot mirror.
    'Android Cronet Builder': {
      'chromium_config': 'android',
      'chromium_apply_config': ['cronet_builder'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder_rel_mb',
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },

    'Android x64 Builder (dbg)': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'x64_builder_mb',
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },

    'Android x86 Builder (dbg)': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'x86_builder_mb',
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },

    'android-kitkat-arm-rel': {
      'chromium_config': 'android',
      'chromium_apply_config': [
        'download_vr_test_apks',
        'mb'
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder',
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
    },

    'android-marshmallow-arm64-rel': {
      'chromium_config': 'android',
      'chromium_apply_config': [
        'download_vr_test_apks',

        # This is specified because 'android-marshmallow-arm64-rel' builder
        # is one of the slowest builder in CQ (crbug.com/804251).
        'goma_high_parallel',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder_mb',
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
    },

    'Cast Android (dbg)' : {
      'chromium_config': 'android',
      'chromium_apply_config': [
          'mb',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'cast_builder',
      'testing': {
        'platform': 'linux',
      },
    },

    'KitKat Phone Tester (dbg)': {
      'chromium_config': 'android',
      'chromium_apply_config': [
          'mb',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder',
      'bot_type': 'tester',
      'parent_buildername': 'Android arm Builder (dbg)',
      'testing': {
        'platform': 'linux',
      },
    },

    'KitKat Phone Tester (rel)': {
      'chromium_config': 'android',
      'chromium_apply_config': [
        'download_vr_test_apks',
        'mb'
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder',
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
    },

    'KitKat Tablet Tester': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder_mb',
      'android_apply_config': ['use_devil_provision'],
      'testing': {
        'platform': 'linux',
      },
    },

    'Marshmallow 64 bit Tester': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm64 Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'arm64_builder_mb',
      'testing': {
        'platform': 'linux',
      },
    },

    'Lollipop Phone Tester': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder_mb',
      'testing': {
        'platform': 'linux',
      },
    },

    'Lollipop Tablet Tester': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder_mb',
      'android_apply_config': ['use_devil_provision'],
      'testing': {
        'platform': 'linux',
      },
    },

    'Marshmallow Phone Tester (rel)': {
      'chromium_config': 'android',
      'chromium_apply_config': [
        'download_vr_test_apks',

        # This is specified because 'android_n5x_swarming_rel' builder
        # is one of the slowest builder in CQ (crbug.com/804251).
        'goma_high_parallel',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder_mb',
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
    },

    'Marshmallow Tablet Tester': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder_mb',
      'android_apply_config': ['use_devil_provision'],
      'testing': {
        'platform': 'linux',
      },
    },

    'Nougat Phone Tester': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm64 Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder_mb',
      'android_apply_config': ['use_devil_provision'],
      'testing': {
        'platform': 'linux',
      },
    },

    'Oreo Phone Tester': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm64 Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'arm64_builder_mb',
      'android_apply_config': ['use_devil_provision'],
      'testing': {
        'platform': 'linux',
      },
    },

    'Android WebView L (dbg)': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder_mb',
      'android_apply_config': ['remove_all_system_webviews'],
      'testing': {
        'platform': 'linux',
      },
    },

    'Android WebView M (dbg)': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder_mb',
      'android_apply_config': ['remove_all_system_webviews'],
      'testing': {
        'platform': 'linux',
      },
    },

    'Android WebView N (dbg)': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm64 Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'arm64_builder_mb',
      'android_apply_config': ['remove_all_system_webviews'],
      'testing': {
        'platform': 'linux',
      },
    },

    'Android WebView O (dbg)': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm64 Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'arm64_builder_mb',
      'android_apply_config': ['remove_all_system_webviews', 'restart_usb'],
      'testing': {
        'platform': 'linux',
      },
    },
  },
}


def stock_cronet_config(name, config='Release', **kwargs):
  bot_config = {
    'android_config': 'main_builder',
    'chromium_config': 'android',
    'chromium_apply_config': [
        'cronet_builder',
        'mb',
        'ninja_confirm_noop',
    ],
    'chromium_config_kwargs': {
      'BUILD_CONFIG': config,
      'TARGET_PLATFORM': 'android',
    },
    'chromium_tests_apply_config': ['staging'],
    'gclient_config': 'chromium',
    'gclient_apply_config': ['android'],
    'bot_type': 'builder_tester',
    'testing': {
      'platform': 'linux',
    },
  }

  bot_config.update(**kwargs)
  return name, bot_config


SPEC['builders'].update([
  stock_cronet_config('android-cronet-arm-dbg', config='Debug'),
  stock_cronet_config('android-cronet-arm-rel'),
  stock_cronet_config('android-cronet-arm64-dbg', config='Debug'),
  stock_cronet_config('android-cronet-arm64-rel'),
  stock_cronet_config('android-cronet-asan-arm-rel'),
  stock_cronet_config('android-cronet-kitkat-arm-rel',
      bot_type='tester',
      parent_buildername='android-cronet-arm-rel'),
  stock_cronet_config('android-cronet-lollipop-arm-rel',
      bot_type='tester',
      parent_buildername='android-cronet-arm-rel'),
  stock_cronet_config('android-cronet-marshmallow-arm64-rel',
      bot_type='tester',
      parent_buildername='android-cronet-arm64-rel'),
  stock_cronet_config('android-cronet-x86-dbg'),
  stock_cronet_config('android-cronet-x86-rel'),
])
