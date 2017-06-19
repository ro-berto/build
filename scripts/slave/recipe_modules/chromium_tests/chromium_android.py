# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

RESULTS_URL = 'https://chromeperf.appspot.com'


SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-android-archive',
  },
  'builders': {
    'Android arm Builder (dbg)': {
      'chromium_config': 'android',
      'enable_swarming': True,
      'chromium_apply_config': [
        'chrome_with_codecs',
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
      'enable_swarming': True,
      'chromium_config': 'android',
      'chromium_apply_config': [
        'chrome_with_codecs',
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

    'Android Cronet Builder (dbg)': {
      'enable_swarming': True,
      'chromium_config': 'main_builder_mb',
      'chromium_apply_config': ['cronet_builder'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder_mb',
      'android_apply_config': ['use_devil_provision'],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
      'tests': {
        steps.SizesStep(RESULTS_URL, 'android_cronet_builder_dbg')
      },
    },

    'Android Cronet Builder Asan': {
      'enable_swarming': True,
      'chromium_config': 'main_builder_rel_mb',
      'chromium_apply_config': ['chromium_asan', 'cronet_builder', 'mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder_rel_mb',
      'android_apply_config': ['asan_symbolize', 'use_devil_provision'],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
    },

    'Android Cronet KitKat Builder': {
      'enable_swarming': True,
      'chromium_config': 'main_builder_rel_mb',
      'chromium_apply_config': ['cronet_builder', 'cronet_official'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder_rel_mb',
      'android_apply_config': ['use_devil_provision'],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
      'tests': {
        steps.SizesStep(RESULTS_URL, 'android_cronet_builder')
      },
    },

    'Android Cronet Lollipop Builder': {
      'enable_swarming': True,
      'chromium_config': 'main_builder_rel_mb',
      'chromium_apply_config': ['cronet_builder', 'cronet_official'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder_rel_mb',
      'android_apply_config': ['use_devil_provision'],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
      'tests': {
        steps.SizesStep(RESULTS_URL, 'android_cronet_l_builder')
      },
    },

    'Android Cronet Marshmallow 64bit Builder': {
      'enable_swarming': True,
      'chromium_config': 'arm64_builder_rel_mb',
      'chromium_apply_config': ['cronet_builder', 'cronet_official'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'arm64_builder_rel_mb',
      'android_apply_config': ['use_devil_provision'],
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
      'tests': {
        steps.SizesStep(RESULTS_URL, 'android_cronet_m64_builder')
      },
    },

    'Android MIPS Builder (dbg)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['chrome_with_codecs'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'mipsel_builder_mb',
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },

    'Android x64 Builder (dbg)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['chrome_with_codecs'],
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
      'chromium_apply_config': ['chrome_with_codecs'],
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

    'KitKat Tablet Tester': {
      'enable_swarming': True,
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
      'test_results_config': 'public_server',
      'test_results_config': 'public_server',
      'testing': {
        'platform': 'linux',
      },
    },

    'Marshmallow 64 bit Tester': {
      'enable_swarming': True,
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
      'test_results_config': 'public_server',
      'test_results_config': 'public_server',
      'testing': {
        'platform': 'linux',
      },
    },

    'Lollipop Phone Tester': {
      'enable_swarming': True,
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
      'test_results_config': 'public_server',
      'testing': {
        'platform': 'linux',
      },
    },

    'Lollipop Tablet Tester': {
      'enable_swarming': True,
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
      'test_results_config': 'public_server',
      'testing': {
        'platform': 'linux',
      },
    },

    'Marshmallow Tablet Tester': {
      'enable_swarming': True,
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
      'test_results_config': 'public_server',
      'testing': {
        'platform': 'linux',
      },
    },

    'Android N5X Swarm Builder': {
      'enable_swarming': True,
      'chromium_config': 'android',
      'chromium_apply_config': [
        'chrome_with_codecs',
        'download_vr_test_apks',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder_mb',
      'test_results_config': 'public_server',
      'bot_type': 'builder_tester',
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
      'test_results_config': 'public_server',
      'tests': [
        steps.AndroidInstrumentationTest('SystemWebViewShellLayoutTest',
                                         result_details=True),
        steps.WebViewCTSTest('L'),
      ],
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
      'test_results_config': 'public_server',
      'android_apply_config': ['remove_all_system_webviews'],
      'tests': [
        steps.AndroidInstrumentationTest('SystemWebViewShellLayoutTest',
                                         result_details=True),
        steps.AndroidInstrumentationTest('WebViewUiTest',
                                         result_details=True),
        steps.WebViewCTSTest('M'),
      ],
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
      'test_results_config': 'public_server',
      'android_apply_config': ['remove_all_system_webviews'],
      'tests': [
        steps.AndroidInstrumentationTest('SystemWebViewShellLayoutTest',
                                         result_details=True),
        steps.WebViewCTSTest('N'),
      ],
      'testing': {
        'platform': 'linux',
      },
    },
  },
}
