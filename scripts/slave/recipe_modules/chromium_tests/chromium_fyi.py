# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy
import time

from . import chromium
from . import chromium_chromiumos
from . import chromium_clang
from . import chromium_linux
from . import chromium_mac
from . import chromium_win
from . import steps

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
      'chromium_tests_apply_config': [ 'staging' ],
      'test_results_config': 'staging_server',
      'testing': {
          'platform': platform,
      },
  }


def chromium_apply_configs(base_config, config_names):
  """chromium_apply_configs returns new config from base config with config.

  It adds config names in chromium_apply_config.

  Args:
    base_config: config obj in SPEC['builders'][x].
    config_names: a list of config names to be added into chromium_apply_config.
  Returns:
    new config obj.
  """
  config = copy.deepcopy(base_config)
  config['chromium_apply_config'].extend(config_names)
  return config


def no_archive(base_config):
  """no_archive returns new config from base config without archive_build etc.

  Args:
    base_config: config obj in SPEC['builders'][x].
  Returns:
    new config obj.
  """
  config = copy.deepcopy(base_config)
  if 'archive_build' in config:
    del(config['archive_build'])
  if 'gs_bucket' in config:
    del(config['gs_bucket'])
  if 'gs_acl' in config:
    del(config['gs_acl'])
  return config


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
    'Chromium Mac 10.13': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'swarming_dimensions': {
        # This can be removed once (if?) we get 10.13 VMs.
        'gpu': '8086:0a2e',
        'os': 'Mac-10.13',
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
      'archive_build': False,
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
    },
    'WebKit Linux root_layer_scrolls Dummy Builder': {
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
    'Fuchsia ARM64': {
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
      # Serialize the tests so as to not overwhelm the limited number of bots.
      'serialize_tests': True,
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
    },

    'Win Builder Localoutputcache': chromium_apply_configs(
        no_archive(chromium_win.SPEC['builders']['Win Builder']),
        ['goma_localoutputcache']),

    'Win Builder Goma Canary': chromium_apply_configs(
        chromium_win.SPEC['builders']['Win Builder'], ['goma_canary']),
    'Win Builder (dbg) Goma Canary': chromium_apply_configs(
        chromium_win.SPEC['builders']['Win Builder (dbg)'],
        ['goma_canary', 'shared_library']),
    'Win Goma Canary LocalOutputCache': chromium_apply_configs(
        no_archive(chromium.SPEC['builders']['Win']),
        ['goma_canary', 'goma_localoutputcache']),
    'Win cl.exe Goma Canary LocalOutputCache': chromium_apply_configs(
        no_archive(chromium.SPEC['builders']['Win']),
        ['goma_canary', 'goma_localoutputcache']),
    'Win7 Builder Goma Canary': chromium_apply_configs(
        chromium_win.SPEC['builders']['Win Builder'], ['goma_canary']),
    'Win7 Builder (dbg) Goma Canary': chromium_apply_configs(
        chromium_win.SPEC['builders']['Win Builder (dbg)'],
        ['goma_canary']),
    'WinMSVC64 Goma Canary': chromium_apply_configs(
        chromium_win.SPEC['builders']['WinMSVC64'],
        ['goma_canary']),
    'chromeos-amd64-generic-rel-goma-canary': chromium_apply_configs(
        chromium_chromiumos.SPEC['builders'][
            'chromeos-amd64-generic-rel'],
        ['goma_canary']),
    'Linux Builder Goma Canary': chromium_apply_configs(
        chromium_linux.SPEC['builders']['Linux Builder'], ['goma_canary']),
    'Linux x64 Goma Canary (clobber)': chromium_apply_configs(
        no_archive(chromium.SPEC['builders']['Linux x64']), ['goma_canary']),
    'Linux x64 Goma Canary LocalOutputCache': chromium_apply_configs(
        no_archive(chromium.SPEC['builders']['Linux x64']),
        ['goma_canary', 'goma_localoutputcache']),
    'Mac Builder Goma Canary': chromium_apply_configs(
        chromium_mac.SPEC['builders']['Mac Builder'], ['goma_canary']),
    'Mac Builder (dbg) Goma Canary': chromium_apply_configs(
        chromium_mac.SPEC['builders']['Mac Builder (dbg)'], ['goma_canary']),
    'Mac Goma Canary (clobber)': chromium_apply_configs(
        no_archive(chromium.SPEC['builders']['Mac']), ['goma_canary']),
    'Mac Builder (dbg) Goma Canary (clobber)': chromium_apply_configs(
        chromium_mac.SPEC['builders']['Mac Builder (dbg)'],
        ['goma_canary', 'clobber']),
    'Mac Goma Canary LocalOutputCache': chromium_apply_configs(
        no_archive(chromium.SPEC['builders']['Mac']),
        ['goma_canary', 'goma_localoutputcache']),

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
      'tests': [
        steps.LocalGTestTest('remoting_unittests'),
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
        steps.LocalGTestTest('base_unittests'),
      ],
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
    },
    'Mojo Android': {
      'chromium_config': 'android',
      'chromium_apply_config': ['android'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'builder_tester',
      'android_config': 'arm64_builder_mb',
      'root_devices': True,
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
    },
  },
}

SPEC['builders']['Android Builder (dbg) Goma Canary'] = chromium_apply_configs(
    SPEC['builders']['Android Builder (dbg)'],
    ['goma_canary'])

SPEC['builders'].update([
    stock_config('Jumbo Linux x64'),
    stock_config('Jumbo Mac'),
    stock_config('Jumbo Win x64'),
    stock_config('VR Linux'),
    stock_config('Leak Detection Linux'),
    stock_config('Linux Viz'),
])
