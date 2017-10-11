# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps
import time

RESULTS_URL = 'https://chromeperf.appspot.com'


KITCHEN_TEST_SPEC = {
  'chromium_config': 'chromium',
  'chromium_apply_config': [
    'mb',
    'ninja_confirm_noop',
    'chrome_with_codecs'
  ],
  'gclient_config': 'chromium',
  'chromium_config_kwargs': {
    'BUILD_CONFIG': 'Release',
    'TARGET_BITS': 64,
  },
  'compile_targets': [
    'all',
  ],
  'testing': {
    'platform': 'linux',
  },
  'enable_swarming': True,
}

def stock_config(name, platform=None, config='Release'):
  if platform is None:
    if 'Mac' in name:
      platform = 'mac'
    elif 'Win' in name:
      platform = 'win'
    elif 'Linux' in name:
      platform = 'linux'
  assert(platform)

  return name, {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_apply_config': [
          'mb',
          'ninja_confirm_noop',
        ],
      'chromium_config_kwargs': {
          'BUILD_CONFIG': config,
          'TARGET_BITS': 64,
        },
      'test_results_config': 'staging_server',
      'testing': {
          'platform': platform,
        },
  }



SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-fyi-archive',
  },
  'builders': {
    'Chromium Mac 10.10 MacViews': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_apply_config': [
        'chromium_mac_mac_views',
        'mb',
      ],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'checkout_dir': 'mac',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'mac',
      },
    },
    'Chromium Mac 10.11': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'mac',
      },
    },
    'Chromium Mac 10.11 Force Mac Toolchain': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'force_mac_toolchain_override'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'mac',
      },
    },
    'Chromium Mac 10.13': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'mac',
      },
    },
    'Linux ARM': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_ARCH': 'arm',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
      'archive_build': True,
      'gs_bucket': 'chromium-fyi-archive',
      'enable_swarming': True,
      'swarming_dimensions': {
        'cpu': 'armv7l-32',
        'os': 'Ubuntu-14.04',
      },
    },
    # There are no slaves for the following two "Dummy Builders" and they
    # do not appear on the actual continuous waterfall; this configuration
    # is here so that a try bot can be added.
    'WebKit Linux slimming_paint_v2 Dummy Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb','ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'blink_tests',
      ],
      'tests': [],
      'test_results_config': 'staging_server',
      'testing': {
          'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'WebKit Linux layout_ng Dummy Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb','ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'blink_tests',
      ],
      'tests': [],
      'test_results_config': 'staging_server',
      'testing': {
          'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'WebKit Linux - RandomOrder':{
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb','ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_results_config': 'staging_server',
      'testing': {
          'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'WebKit Mac - RandomOrder':{
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb','ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_results_config': 'staging_server',
      'testing': {
          'platform': 'mac',
      },
      'enable_swarming': True,
    },
    'WebKit Win - RandomOrder':{
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb','ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'compile_targets': [
        'blink_tests',
      ],
      'tests': [
        steps.BlinkTest(extra_args=[
          '--seed=4',
        ]),
      ],
      'testing': {
          'platform': 'win',
      },
      'enable_swarming': True,
    },
    'Print Preview Linux': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'GYP_DEFINES': {
        'component': 'shared_library',
      },
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'linux',
        'TARGET_BITS': 64,
      },
      'tests': [
        steps.PrintPreviewTests(),
      ],
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
    },
    'Print Preview Mac': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'GYP_DEFINES': {
        'component': 'shared_library',
      },
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'mac',
        'TARGET_BITS': 64,
      },
      'tests': [
        steps.PrintPreviewTests(),
      ],
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'mac',
      },
    },
    'Print Preview Win': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'GYP_DEFINES': {
        'component': 'shared_library',
      },
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'win',
        'TARGET_BITS': 32,
      },
      'tests': [
        steps.PrintPreviewTests(),
      ],
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
    },
    'Fuchsia': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['fuchsia'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'fuchsia',
      },
      'bot_type': 'builder_tester',
      'checkout_dir': 'linux',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
    },
    'Fuchsia (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['fuchsia'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'fuchsia',
      },
      'bot_type': 'builder',
      'checkout_dir': 'linux',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
    },
    'Mac OpenSSL': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'GYP_DEFINES': {
        'use_openssl': '1',
      },
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'mac',
      },
    },
    'Ozone Linux': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ozone'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [],
      'checkout_dir': 'linux',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'Site Isolation Android': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'content_unittests',
        'content_browsertests',
      ],
      'android_config': 'arm64_builder_mb',
      'root_devices': True,
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'Site Isolation Linux': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'GYP_DEFINES': {
        'dcheck_always_on': '1',
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'content_unittests',
        'content_browsertests',
      ],
      'checkout_dir': 'linux',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'Site Isolation Win': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'win',
        'TARGET_BITS': 32,
      },
      'GYP_DEFINES': {
        'dcheck_always_on': '1',
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'content_unittests',
        'content_browsertests',
      ],
      'tests': [
        steps.BlinkTest(extra_args=[
          '--additional-driver-flag',
          '--site-per-process',
          '--additional-expectations',
          'src\\third_party\\WebKit\\LayoutTests\\FlagExpectations\\site-per-process',
        ]),
      ],
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'Browser Side Navigation Linux': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'content_unittests',
        'content_browsertests',
      ],
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'CrWinGoma': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary', 'mb', 'goma_high_parallel'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'compile_targets': [ 'chrome' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win'
      }
    },
    'CrWinGoma(dll)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary','mb', 'shared_library',
                                'goma_high_parallel'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'compile_targets': [ 'chrome' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win'
      }
    },
    'CrWinGoma(loc)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['clobber', 'goma_canary', 'shared_library',
                                'goma_localoutputcache', 'mb',
                                'goma_high_parallel'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'compile_targets': [ 'all' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win'
      }
    },
    'CrWin7Goma': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary', 'mb', 'goma_high_parallel'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'compile_targets': [ 'chrome' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win'
      }
    },
    'CrWin7Goma(dll)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary', 'mb', 'goma_high_parallel',
                                'shared_library'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'compile_targets': [ 'chrome' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win'
      }
    },
    'CrWin7Goma(dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary', 'mb', 'goma_high_parallel'],
      'gclient_config': 'chromium',
      'GYP_DEFINES': {
        'win_z7': '1'
      },
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'compile_targets': [ 'chrome' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win'
      }
    },
    'CrWin7Goma(clbr)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['clobber', 'goma_canary', 'mb',
                                'shared_library', 'goma_high_parallel'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'compile_targets': [ 'all' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win'
      }
    },
    'CrWinClangGoma': {
      'chromium_config': 'chromium_win_clang_official',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['goma_canary', 'mb', 'goma_high_parallel'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'compile_targets': [
        'all',
      ],
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,

      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
    },
    # followed amd64-generic config in chromium_tests/chromium_chromiumos.py
    'ChromeOS amd64 Chromium Goma Canary': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['chromeos', 'goma_canary', 'mb',
                                'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'chromeos',
        'TARGET_CROS_BOARD': 'amd64-generic',
      },
      'compile_targets': [ 'chromiumos_preflight' ],
      'goma_canary': True,
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux'
      }
    },
    'Chromium Linux Goma Canary': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [ 'chrome' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux'
      }
    },
    'Chromium Linux Goma Canary (clobber)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['clobber', 'goma_canary', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [ 'all' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux'
      }
    },
    'Chromium Linux Goma Canary LocalOutputCache': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['clobber', 'goma_canary',
                                'goma_localoutputcache', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [ 'all' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux'
      }
    },
    'Chromium Mac 10.9 Goma Canary': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [ 'chrome' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'mac'
      }
    },
    'Chromium Mac 10.9 Goma Canary (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['goma_canary', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'compile_targets': [ 'chrome' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'mac'
      }
    },
    'Chromium Mac 10.9 Goma Canary (clobber)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'clobber',
        'goma_canary',
        'mb',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'compile_targets': [ 'all' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'mac'
      }
    },
    'Chromium Mac 10.9 Goma Canary (dbg)(clobber)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'clobber',
        'goma_canary',
        'mb',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'compile_targets': [ 'all' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'mac'
      }
    },
    'Chromium Mac Goma Canary LocalOutputCache': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'clobber',
        'goma_canary',
        'goma_localoutputcache',
        'mb',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'compile_targets': [ 'all' ],
      'goma_canary': True,
      'tests': steps.GOMA_TESTS,
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'mac'
      }
    },
    'Android Builder Goma Canary (dbg)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['goma_canary', 'chrome_with_codecs', 'mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder',
      'goma_canary': True,
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
    },
    'Win Builder (ANGLE)': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
      'patch_root': 'src/third_party/angle',
      'enable_swarming': True,
    },
    'Win7 Tests (ANGLE)': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'Win Builder (ANGLE)',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },

    'Headless Linux (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ozone'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'linux',
      },
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
    },

    'Android Builder (dbg)': {
      'chromium_config': 'android',
      'chromium_apply_config': [
        'chrome_with_codecs',
        'mb',
        'download_vr_test_apks'
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder',
      'bot_type': 'builder',
      'compile_targets': [
        'chromedriver_webview_shell_apk',
      ],
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
    },

    'Android Remoting Tests': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'compile_targets': [
          'remoting_apk',
      ],
      'parent_buildername': 'Android Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder',
      'root_devices': True,
      'enable_swarming': False,
      'tests': [
        steps.GTestTest('remoting_unittests'),
        steps.AndroidInstrumentationTest('ChromotingTest'),
      ],
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
    },
    'Android Find Annotated Test': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder_mb',
      'android_apply_config': ['remove_all_system_webviews'],
      'tests': [
        steps.FindAnnotatedTest(),
      ],
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
    },
    'Android Asan Builder Tests (dbg)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'builder_tester',
      'android_config': 'clang_tests',
      'root_devices': True,
      'tests': [
        steps.AndroidInstrumentationTest('ChromePublicTest', tool='asan'),
        steps.AndroidInstrumentationTest('ContentShellTest', tool='asan'),
        steps.AndroidInstrumentationTest('ChromeSyncShellTest', tool='asan'),
        steps.AndroidInstrumentationTest(
            'WebViewInstrumentationTest', tool='asan'),
      ],
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
    },
    'Win 10 Fast Ring': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'GYP_DEFINES': {
        'dcheck_always_on': '1',
      },
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
    },
    'Android Coverage (dbg)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'tester',
      'parent_buildername': 'Android Builder (dbg)',
      'android_config': 'incremental_coverage_builder_tests',
      'root_devices': True,
      'checkout_dir': 'android',
      'tests': [
        steps.AndroidInstrumentationTest('ChromePublicTest'),
        steps.AndroidInstrumentationTest('ContentShellTest'),
        steps.AndroidInstrumentationTest('ChromeSyncShellTest'),
        steps.AndroidInstrumentationTest('WebViewInstrumentationTest'),
        steps.IncrementalCoverageTest(),
      ],
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
    },
    'Win SyzyAsan (rel)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
          'mb',
          'syzyasan_compile_only',
          'shared_library',
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'win',
        'TARGET_BITS': 32,
      },
      'compile_targets': [
        'chrome',
      ],
      'enable_swarming': True,
      'checkout_dir': 'win',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
    },
    'Android VR Tests': {
      'chromium_config': 'android',
      'chromium_apply_config': ['download_vr_test_apks'],
      'gclient_config': 'chromium',
      'gclient_apply_config': [
        'android',
      ],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'tester',
      'parent_buildername': 'Android Builder (dbg)',
      'android_config': 'main_builder_mb',
      'android_apply_config': [
        'use_devil_provision',
        'remove_system_vrcore',
      ],
      'root_devices': True,
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'Linux remote_run Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
        'ninja_confirm_noop',
        'chrome_with_codecs'
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'Linux remote_run Tester': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
        'ninja_confirm_noop',
        'chrome_with_codecs'
      ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'Linux remote_run Builder',
      'tests': [
        steps.GTestTest('base_unittests'),
      ],
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'Mojo ChromiumOS': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['chromeos', 'mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'chromeos',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': { 'platform': 'linux', },
      'enable_swarming': True,
    },
    'Mojo Linux': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'Mojo Windows': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'win',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': { 'platform': 'win', },
      'enable_swarming': True,
    },

    'Out of Process Profiling Android': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'builder_tester',
      'serialize_tests': True,
      'test_results_config': 'staging_server',
      'testing': { 'platform': 'linux', },
    },

    'Out of Process Profiling Linux': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'serialize_tests': True,
      'test_results_config': 'staging_server',
      'testing': { 'platform': 'linux', },
    },

    'Out of Process Profiling Mac': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'serialize_tests': True,
      'test_results_config': 'staging_server',
      'testing': { 'platform': 'mac', },
    },

    'Out of Process Profiling Windows': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'serialize_tests': True,
      'test_results_config': 'staging_server',
      'testing': { 'platform': 'win', },
    },

    'Linux Clang Analyzer': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'analysis'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },

    # There are no slaves for the following "dummy builders" and they
    # do not appear on the actual continuous waterfall; these configurations
    # are here so that trybots can be added.
    'ChromiumOS amd64-generic Dummy Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['chromeos', 'mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'chromeos',
        'TARGET_CROS_BOARD': 'amd64-generic',
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'linux',
      },
    },
    'ChromiumOS daisy Dummy Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['chromeos', 'mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'chromeos',
        'TARGET_CROS_BOARD': 'daisy',
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'linux',
      },
    },
  }
}


SPEC['builders'].update([
    stock_config('Jumbo Linux x64'),
    stock_config('Jumbo Mac'),
    stock_config('Jumbo Win x64'),
])
