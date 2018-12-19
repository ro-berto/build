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

def stock_config(name, config='Release', target_bits=64, staging=True,
                 **kwargs):
  if 'mac' in name.lower():
    platform = 'mac'
  elif 'win' in name.lower():
    platform = 'win'
  elif 'linux' in name.lower():
    platform = 'linux'
  assert(platform)

  bot_config = {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_apply_config': [
          'mb',
          'ninja_confirm_noop',
      ],
      'chromium_config_kwargs': {
          'BUILD_CONFIG': config,
          'TARGET_BITS': target_bits,
      },
      'chromium_tests_apply_config': [],
      'testing': {
          'platform': platform,
      },
  }
  bot_config.update(**kwargs)
  if staging:
    bot_config['chromium_tests_apply_config'].append('staging')
    bot_config['test_results_config'] = 'staging_server'
  return name, bot_config


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


def no_compile_targets(base_config):
  """no_compile_targets returns new config from base config without
  compile_targets.

  Args:
    base_config: config obj in SPEC['builders'][x].
  Returns:
    new config obj.
  """

  config = copy.deepcopy(base_config)

  return config


def override_compile_targets(base_config, compile_targets):
  """Overrides compile_targets.

  Args:
    base_config: config obj in SPEC['builders'][x].
    compile_targets: new compile targets.
  Returns:
    new config obj.
  """

  config = copy.deepcopy(base_config)
  config['compile_targets'] = compile_targets
  return config


SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-fyi-archive',
  },
  'builders': {
    'mac-osxbeta-rel': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'swarming_dimensions': {
        'os': 'Mac-10.14',
      },
      'bot_type': 'tester',
      'checkout_dir': 'mac',
      'test_results_config': 'staging_server',
      'parent_mastername': 'chromium.mac',
      'parent_buildername': 'Mac Builder',
      'testing': {
        'platform': 'mac',
      },
    },
    'mac-views-rel': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['mb'],
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
      'checkout_dir': 'mac',
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
      'gclient_apply_config': ['arm'],
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
    },
    # There are no slaves for the following two "Dummy Builders" and they
    # do not appear on the actual continuous waterfall; this configuration
    # is here so that a try bot can be added.
    'WebKit Linux composite_after_paint Dummy Builder': {
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
    # TODO(crbug.com/909899): Remove this configuration after
    # crrev.com/c/1367655 lands.
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
    # TODO(jbudorick): Remove these three once the bots have been renamed.
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
    'fuchsia-fyi-arm64-rel': {
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
      # Serialize the tests to limit capacity usage.
      'serialize_tests': True,
      'checkout_dir': 'linux',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
    },
    'fuchsia-fyi-x64-dbg': {
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
      # Serialize the tests to limit capacity usage.
      'serialize_tests': True,
      'checkout_dir': 'linux',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
    },
    'fuchsia-fyi-x64-rel': {
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
      # Serialize the tests to limit capacity usage.
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

    'Win Builder Localoutputcache': chromium_apply_configs(
        no_archive(chromium_win.SPEC['builders']['Win Builder']),
        ['goma_localoutputcache']),

    'Win Builder Goma Canary': chromium_apply_configs(
        chromium_win.SPEC['builders']['Win Builder'],
        ['goma_canary', 'goma_use_local']),
    'Win Builder (dbg) Goma Canary': chromium_apply_configs(
        chromium_win.SPEC['builders']['Win Builder (dbg)'],
        ['goma_canary']),
    'Win Goma Canary LocalOutputCache': chromium_apply_configs(
        no_archive(chromium.SPEC['builders']['win-rel']),
        ['goma_canary', 'goma_localoutputcache']),
    'Win cl.exe Goma Canary LocalOutputCache': chromium_apply_configs(
        no_compile_targets(no_archive(chromium.SPEC['builders']['win-rel'])),
        ['goma_canary', 'goma_localoutputcache']),
    'Win7 Builder Goma Canary': chromium_apply_configs(
        chromium_win.SPEC['builders']['Win Builder'], ['goma_canary']),
    'Win7 Builder (dbg) Goma Canary': chromium_apply_configs(
        chromium_win.SPEC['builders']['Win Builder (dbg)'],
        ['goma_canary']),
    'WinMSVC64 Goma Canary': chromium_apply_configs(
        {
          'chromium_config': 'chromium',
          'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
          'gclient_config': 'chromium',
          'chromium_config_kwargs': {
            'BUILD_CONFIG': 'Release',
            'TARGET_PLATFORM': 'win',
            'TARGET_BITS': 64,
          },
          'bot_type': 'builder',
          'checkout_dir': 'win',
          'testing': {
            'platform': 'win',
          },
          # Workaround so that recipes doesn't add random build targets to our
          # compile line. We want to build everything.
          'add_tests_as_compile_targets': False,
        },
        ['goma_canary']),
    'chromeos-amd64-generic-rel-goma-canary': chromium_apply_configs(
        chromium_chromiumos.SPEC['builders'][
            'chromeos-amd64-generic-rel'],
        ['goma_canary']),
    'Linux Builder Goma Canary': chromium_apply_configs(
        chromium_linux.SPEC['builders']['Linux Builder'],
        ['goma_canary','goma_use_local']),
    'Linux x64 Goma Canary (clobber)': chromium_apply_configs(
        no_archive(chromium.SPEC['builders']['linux-rel']), ['goma_canary']),
    'Linux x64 Goma Canary LocalOutputCache': chromium_apply_configs(
        no_archive(chromium.SPEC['builders']['linux-rel']),
        ['goma_canary', 'goma_localoutputcache']),
    'Mac Builder Goma Canary': chromium_apply_configs(
        chromium_mac.SPEC['builders']['Mac Builder'],
        ['goma_canary', 'goma_use_local']),
    'Mac Builder (dbg) Goma Canary': chromium_apply_configs(
        chromium_mac.SPEC['builders']['Mac Builder (dbg)'], ['goma_canary']),
    'Mac Goma Canary (clobber)': chromium_apply_configs(
        no_archive(chromium.SPEC['builders']['mac-rel']), ['goma_canary']),
    'Mac Builder (dbg) Goma Canary (clobber)': chromium_apply_configs(
        chromium_mac.SPEC['builders']['Mac Builder (dbg)'],
        ['goma_canary', 'clobber']),
    # Mac has less disks, so use small localoutputcache.
    # Build chrome only. Even with smaller localoutputcache, disk is short.
    # See crbug.com/825536
    'Mac Goma Canary LocalOutputCache': chromium_apply_configs(
        override_compile_targets(
            no_archive(chromium.SPEC['builders']['mac-rel']), ['chrome']),
        ['goma_canary', 'goma_localoutputcache_small']),

    # Latest Goma Client
    'Win Builder Goma Latest Client': chromium_apply_configs(
        chromium_win.SPEC['builders']['Win Builder'],
        ['goma_latest_client', 'goma_use_local']),
    'Win Builder (dbg) Goma Latest Client': chromium_apply_configs(
        chromium_win.SPEC['builders']['Win Builder (dbg)'],
        ['goma_latest_client']),
    'Win Goma Latest Client LocalOutputCache': chromium_apply_configs(
        no_archive(chromium.SPEC['builders']['win-rel']),
        ['goma_latest_client', 'goma_localoutputcache']),
    'Win cl.exe Goma Latest Client LocalOutputCache': chromium_apply_configs(
        no_compile_targets(no_archive(chromium.SPEC['builders']['win-rel'])),
        ['goma_latest_client', 'goma_localoutputcache']),
    'Win7 Builder Goma Latest Client': chromium_apply_configs(
        chromium_win.SPEC['builders']['Win Builder'], ['goma_latest_client']),
    'Win7 Builder (dbg) Goma Latest Client': chromium_apply_configs(
        chromium_win.SPEC['builders']['Win Builder (dbg)'],
        ['goma_latest_client']),
    'WinMSVC64 Goma Latest Client': chromium_apply_configs(
        {
          'chromium_config': 'chromium',
          'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
          'gclient_config': 'chromium',
          'chromium_config_kwargs': {
            'BUILD_CONFIG': 'Release',
            'TARGET_PLATFORM': 'win',
            'TARGET_BITS': 64,
          },
          'bot_type': 'builder',
          'checkout_dir': 'win',
          'testing': {
            'platform': 'win',
          },
          # Workaround so that recipes doesn't add random build targets to our
          # compile line. We want to build everything.
          'add_tests_as_compile_targets': False,
        },
        ['goma_latest_client']),
    'chromeos-amd64-generic-rel-goma-latest-client': chromium_apply_configs(
        chromium_chromiumos.SPEC['builders'][
            'chromeos-amd64-generic-rel'],
        ['goma_latest_client']),
    # For building targets instrumented for code coverage.
    'linux-code-coverage':{
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb',
        'ninja_confirm_noop',
        'goma_high_parallel',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['use_clang_coverage'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
      'checkout_dir': 'linux',
    },
    'Linux Builder Goma Latest Client': chromium_apply_configs(
        chromium_linux.SPEC['builders']['Linux Builder'],
        ['goma_latest_client','goma_use_local']),
    'Linux x64 Goma Latest Client (clobber)': chromium_apply_configs(
        no_archive(chromium.SPEC['builders']['linux-rel']),
        ['goma_latest_client']),
    'Linux x64 Goma Latest Client LocalOutputCache': chromium_apply_configs(
        no_archive(chromium.SPEC['builders']['linux-rel']),
        ['goma_latest_client', 'goma_localoutputcache']),
    'Mac Builder Goma Latest Client': chromium_apply_configs(
        chromium_mac.SPEC['builders']['Mac Builder'],
        ['goma_latest_client', 'goma_use_local']),
    'Mac Builder (dbg) Goma Latest Client': chromium_apply_configs(
        chromium_mac.SPEC['builders']['Mac Builder (dbg)'],
        ['goma_latest_client']),
    'Mac Goma Latest Client (clobber)': chromium_apply_configs(
        no_archive(chromium.SPEC['builders']['mac-rel']),
        ['goma_latest_client']),
    'Mac Builder (dbg) Goma Latest Client (clobber)': chromium_apply_configs(
        chromium_mac.SPEC['builders']['Mac Builder (dbg)'],
        ['goma_latest_client', 'clobber']),
    # Mac has less disks, so use small localoutputcache.
    # Build chrome only. Even with smaller localoutputcache, disk is short.
    # See crbug.com/825536
    'Mac Goma Latest Client LocalOutputCache': chromium_apply_configs(
        override_compile_targets(
            no_archive(chromium.SPEC['builders']['mac-rel']), ['chrome']),
        ['goma_latest_client', 'goma_localoutputcache_small']),

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
      'chromium_apply_config': ['mb'],
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
      'chromium_apply_config': [
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
      'chromium_apply_config': [
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
      'parent_buildername': 'Android Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder',
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
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
    },
    'Android VR Tests': {
      'chromium_config': 'android',
      'chromium_apply_config': [
        'mb',
        'download_vr_test_apks'
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': [
        'android',
      ],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'bot_type': 'tester',
      'parent_buildername': 'Android Builder (dbg)',
      'android_config': 'main_builder',
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
      # TODO(crbug.com/876570): Here and below, we should move the Mojo
      # builders to a different "master" and get rid of this property; we
      # don't really want different builders on the same master to have
      # different priorities, it makes reasoning about builders harder for
      # sheriffs and troopers.
      'swarming_default_priority': 25,
      'testing': {
        'platform': 'linux',
      },
    },
    'android-mojo-webview-rel': {
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
      'swarming_default_priority': 25,
      'testing': {
        'platform': 'linux',
      },
    },
    'Mojo ChromiumOS': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chromeos'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'linux',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'swarming_default_priority': 25,
      'testing': { 'platform': 'linux', },
    },
    'Mojo Linux': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'swarming_default_priority': 25,
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
    },
    'mac-mojo-rel': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'swarming_default_priority': 25,
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'mac',
      },
    },
    'Mojo Windows': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'swarming_default_priority': 25,
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_PLATFORM': 'win',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder_tester',
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

    'chromeos-amd64-generic-rel-vm-tests': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb', 'ninja_confirm_noop',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chromeos_amd64_generic'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_ARCH': 'intel',
        'TARGET_BITS': 64,
        'TARGET_CROS_BOARD': 'amd64-generic',
        'TARGET_PLATFORM': 'chromeos',
      },
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
      'tests': {},
    },

    'chromeos-kevin-rel-hw-tests': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'mb', 'ninja_confirm_noop',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chromeos_kevin'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_ARCH': 'arm',
        'TARGET_BITS': 32,
        'TARGET_CROS_BOARD': 'kevin',
        'TARGET_PLATFORM': 'chromeos',
      },
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
      'tests': {},
    },

    'linux-autofill-captured-sites-rel': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'linux',
      },
      'bot_type': 'builder_tester',
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'linux',
      },
    },

    'mac-autofill-captured-sites-rel': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'mac',
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'captured_sites_interactive_tests',
      ],
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'mac',
      },
    },

    'win-autofill-captured-sites-rel': {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'win',
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
        'captured_sites_interactive_tests',
      ],
      'test_results_config': 'staging_server',
      'testing': {
        'platform': 'win',
      },
    },
  },
}

SPEC['builders']['Android Builder (dbg) Goma Canary'] = chromium_apply_configs(
    SPEC['builders']['Android Builder (dbg)'],
    ['goma_canary'])
SPEC['builders']['Android Builder (dbg) Goma Latest Client'] = (
    chromium_apply_configs(
        SPEC['builders']['Android Builder (dbg)'],
        ['goma_latest_client']))

SPEC['builders'].update([
    stock_config('linux-blink-rel-dummy', staging=False),
    stock_config('mac10.10-blink-rel-dummy', staging=False),
    stock_config('mac10.11-blink-rel-dummy', staging=False),
    stock_config('mac10.12-blink-rel-dummy', staging=False),
    stock_config('mac10.13_retina-blink-rel-dummy', staging=False),
    stock_config('mac10.13-blink-rel-dummy', staging=False),
    stock_config('win7-blink-rel-dummy', target_bits=32, staging=False),
    stock_config('win10-blink-rel-dummy', target_bits=32, staging=False),
    stock_config('Jumbo Linux x64'),
    stock_config('Jumbo Mac'),
    stock_config('Jumbo Win x64'),
    stock_config('VR Linux'),
    stock_config('Linux Viz'),
    stock_config('linux-annotator-rel'),
    stock_config('linux-blink-animation-use-time-delta', config='Debug'),
    stock_config('linux-blink-gen-property-trees', config='Debug'),
    stock_config('linux-blink-heap-incremental-marking', config='Debug'),
    stock_config('linux-blink-heap-unified-gc',
                 config='Debug',
                 bot_type='tester',
                 parent_mastername='chromium.linux',
                 parent_buildername='Linux Builder (dbg)'),
    stock_config('linux-blink-heap-verification'),
    stock_config('linux-chromium-tests-staging-builder',
                 bot_type='builder'),
    stock_config('linux-chromium-tests-staging-tests',
                 bot_type='tester',
                 parent_buildername='linux-chromium-tests-staging-builder'),
    stock_config('linux-gcc-rel'),
    stock_config('linux-tcmalloc-rel'),
    stock_config('mac-hermetic-upgrade-rel'),
    stock_config('win-annotator-rel'),
])
