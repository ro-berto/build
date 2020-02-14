# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import bot_spec
from . import chromium
from . import chromium_chromiumos
from . import chromium_linux
from . import chromium_mac
from . import chromium_win
from . import steps

RESULTS_URL = 'https://chromeperf.appspot.com'

KITCHEN_TEST_SPEC = {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['mb',],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
    },
    'compile_targets': ['all',],
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
  assert (platform)

  bot_config = {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['mb',],
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
  return name, bot_spec.BotSpec.create(**bot_config)


def chromium_apply_configs(base_config, config_names):
  """chromium_apply_configs returns new config from base config with config.

  It adds config names in chromium_apply_config.

  Args:
    base_config: config obj in SPEC['builders'][x].
    config_names: a list of config names to be added into chromium_apply_config.
  Returns:
    new config obj.
  """
  return base_config.extend(chromium_apply_config=config_names)


def no_archive(base_config):
  """no_archive returns new config from base config without archive_build etc.

  Args:
    base_config: config obj in SPEC['builders'][x].
  Returns:
    new config obj.
  """
  return base_config.evolve(
      archive_build=None, gs_bucket=None, gs_acl=None, gs_build_name=None)


def override_compile_targets(base_config, compile_targets):
  """Overrides compile_targets.

  Args:
    base_config: config obj in SPEC['builders'][x].
    compile_targets: new compile targets.
  Returns:
    new config obj.
  """
  return base_config.evolve(compile_targets=compile_targets)


SPEC = {
    'settings': {
        'build_gs_bucket': 'chromium-fyi-archive',
    },
    'builders': {
        'Mac Builder Next':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'mac',
                },
            ),
        'mac-osxbeta-rel':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                gclient_config='chromium',
                chromium_apply_config=['mb'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                swarming_dimensions={
                    'os': 'Mac-10.14',
                },
                bot_type=bot_spec.TESTER,
                test_results_config='staging_server',
                parent_mastername='chromium.mac',
                parent_buildername='Mac Builder',
                testing={
                    'platform': 'mac',
                },
            ),
        # There are no slaves for the following two "Dummy Builders" and they
        # do not appear on the actual continuous waterfall; this configuration
        # is here so that a try bot can be added.
        'WebKit Linux composite_after_paint Dummy Builder':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                compile_targets=[
                    'blink_tests',
                ],
                tests=[],
                test_results_config='staging_server',
                testing={
                    'platform': 'linux',
                },
            ),
        'WebKit Linux layout_ng_disabled Builder':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                compile_targets=[
                    'blink_tests',
                ],
                tests=[],
                test_results_config='staging_server',
                testing={
                    'platform': 'linux',
                },
            ),
        # TODO(jbudorick): Remove these three once the bots have been renamed.
        'Fuchsia':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                gclient_apply_config=['fuchsia_x64'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'fuchsia',
                },
                bot_type=bot_spec.BUILDER_TESTER,
                test_results_config='staging_server',
                testing={
                    'platform': 'linux',
                },
            ),
        'Fuchsia (dbg)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                gclient_apply_config=['fuchsia_x64'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'fuchsia',
                },
                bot_type=bot_spec.BUILDER,
                test_results_config='staging_server',
                testing={
                    'platform': 'linux',
                },
            ),
        'Fuchsia ARM64':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                gclient_apply_config=['fuchsia_arm64'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'fuchsia',
                },
                bot_type=bot_spec.BUILDER_TESTER,
                # Serialize the tests so as to not overwhelm the limited
                # number of bots.
                serialize_tests=True,
                test_results_config='staging_server',
                testing={
                    'platform': 'linux',
                },
            ),
        'fuchsia-fyi-arm64-rel':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                gclient_apply_config=['fuchsia_arm64', 'fuchsia_arm64_host'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'fuchsia',
                },
                bot_type=bot_spec.BUILDER_TESTER,
                # Serialize the tests to limit capacity usage.
                serialize_tests=True,
                test_results_config='staging_server',
                testing={
                    'platform': 'linux',
                },
            ),
        'fuchsia-fyi-x64-dbg':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                gclient_apply_config=['fuchsia_x64'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'fuchsia',
                },
                bot_type=bot_spec.BUILDER,
                # Serialize the tests to limit capacity usage.
                serialize_tests=True,
                test_results_config='staging_server',
                testing={
                    'platform': 'linux',
                },
            ),
        'fuchsia-fyi-x64-rel':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                gclient_apply_config=['fuchsia_x64'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'fuchsia',
                },
                bot_type=bot_spec.BUILDER_TESTER,
                # Serialize the tests to limit capacity usage.
                serialize_tests=True,
                test_results_config='staging_server',
                testing={
                    'platform': 'linux',
                },
            ),
        'Mac OpenSSL':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                test_results_config='staging_server',
                testing={
                    'platform': 'mac',
                },
            ),
        'Site Isolation Android':
            bot_spec.BotSpec.create(
                chromium_config='android',
                gclient_config='chromium',
                gclient_apply_config=['android'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'android',
                },
                bot_type=bot_spec.BUILDER_TESTER,
                compile_targets=[
                    'content_unittests',
                    'content_browsertests',
                ],
                android_config='arm64_builder_mb',
                test_results_config='staging_server',
                testing={
                    'platform': 'linux',
                },
            ),
        'Win Builder Localoutputcache':
            chromium_apply_configs(
                no_archive(chromium_win.SPEC['builders']['Win Builder']),
                ['goma_localoutputcache']),
        'Win Builder Goma Canary':
            chromium_apply_configs(chromium_win.SPEC['builders']['Win Builder'],
                                   ['goma_canary', 'goma_use_local']),
        'Win Builder (dbg) Goma Canary':
            chromium_apply_configs(
                chromium_win.SPEC['builders']['Win Builder (dbg)'],
                ['goma_canary']),
        'win32-archive-rel-goma-canary-localoutputcache':
            chromium_apply_configs(
                no_archive(chromium.SPEC['builders']['win-archive-rel']),
                ['goma_canary', 'goma_localoutputcache']),

        # TODO(b/139556893): remove after win7 builders removal.
        'Win7 Builder Goma Canary':
            chromium_apply_configs(chromium_win.SPEC['builders']['Win Builder'],
                                   ['goma_canary']),
        'Win7 Builder (dbg) Goma Canary':
            chromium_apply_configs(
                chromium_win.SPEC['builders']['Win Builder (dbg)'],
                ['goma_canary']),
        'chromeos-amd64-generic-rel-goma-canary':
            chromium_apply_configs(
                chromium_chromiumos.SPEC['builders']
                ['chromeos-amd64-generic-rel'], ['goma_canary']),
        'Linux Builder Goma Canary':
            chromium_apply_configs(
                chromium_linux.SPEC['builders']['Linux Builder'],
                ['goma_canary', 'goma_use_local']),
        'linux-archive-rel-goma-canary':
            chromium_apply_configs(
                no_archive(chromium.SPEC['builders']['linux-archive-rel']),
                ['goma_canary']),
        'linux-archive-rel-goma-canary-localoutputcache':
            chromium_apply_configs(
                no_archive(chromium.SPEC['builders']['linux-archive-rel']),
                ['goma_canary', 'goma_localoutputcache']),
        # RBE
        'chromeos-amd64-generic-rel-goma-rbe-canary':
            chromium_apply_configs(
                chromium_chromiumos.SPEC['builders']
                ['chromeos-amd64-generic-rel'], ['goma_canary']),
        'Linux Builder Goma RBE Canary':
            chromium_apply_configs(
                chromium_linux.SPEC['builders']['Linux Builder'],
                ['goma_canary', 'goma_use_local']),
        'linux-archive-rel-goma-rbe-canary':
            chromium_apply_configs(
                no_archive(chromium.SPEC['builders']['linux-archive-rel']),
                ['goma_canary']),
        'linux-archive-rel-goma-rbe-ats-canary':
            chromium_apply_configs(
                no_archive(chromium.SPEC['builders']['linux-archive-rel']),
                ['goma_canary']),
        'Mac Builder Goma Canary':
            chromium_apply_configs(chromium_mac.SPEC['builders']['Mac Builder'],
                                   ['goma_canary', 'goma_use_local']),
        'Mac Builder (dbg) Goma Canary':
            chromium_apply_configs(
                chromium_mac.SPEC['builders']['Mac Builder (dbg)'],
                ['goma_canary']),
        'mac-archive-rel-goma-canary':
            chromium_apply_configs(
                no_archive(chromium.SPEC['builders']['mac-archive-rel']),
                ['goma_canary']),
        'Mac Builder (dbg) Goma Canary (clobber)':
            chromium_apply_configs(
                chromium_mac.SPEC['builders']['Mac Builder (dbg)'],
                ['goma_canary', 'clobber']),
        # Mac has less disks, so use small localoutputcache.
        # Build chrome only. Even with smaller localoutputcache, disk is short.
        # See crbug.com/825536
        'mac-archive-rel-goma-canary-localoutputcache':
            chromium_apply_configs(
                override_compile_targets(
                    no_archive(chromium.SPEC['builders']['mac-archive-rel']),
                    ['chrome']),
                ['goma_canary', 'goma_localoutputcache_small']),
        # RBE
        'mac-archive-rel-goma-rbe-canary':
            chromium_apply_configs(
                no_archive(chromium.SPEC['builders']['mac-archive-rel']),
                ['goma_canary']),
        'Mac Builder (dbg) Goma RBE Canary (clobber)':
            chromium_apply_configs(
                chromium_mac.SPEC['builders']['Mac Builder (dbg)'],
                ['goma_canary', 'clobber']),

        # Latest Goma Client
        'Win Builder Goma Latest Client':
            chromium_apply_configs(chromium_win.SPEC['builders']['Win Builder'],
                                   ['goma_latest_client', 'goma_use_local']),
        'Win Builder (dbg) Goma Latest Client':
            chromium_apply_configs(
                chromium_win.SPEC['builders']['Win Builder (dbg)'],
                ['goma_latest_client']),
        'win32-archive-rel-goma-latest-localoutputcache':
            chromium_apply_configs(
                no_archive(chromium.SPEC['builders']['win-archive-rel']),
                ['goma_latest_client', 'goma_localoutputcache']),
        # RBE
        'Win Builder Goma RBE Latest Client':
            chromium_apply_configs(chromium_win.SPEC['builders']['Win Builder'],
                                   ['goma_latest_client', 'goma_use_local']),
        'Win Builder (dbg) Goma RBE Latest Client':
            chromium_apply_configs(
                chromium_win.SPEC['builders']['Win Builder (dbg)'],
                ['goma_latest_client']),

        # TODO(b/139556893): remove after removal of win7.
        'Win7 Builder Goma Latest Client':
            chromium_apply_configs(chromium_win.SPEC['builders']['Win Builder'],
                                   ['goma_latest_client']),
        'Win7 Builder (dbg) Goma Latest Client':
            chromium_apply_configs(
                chromium_win.SPEC['builders']['Win Builder (dbg)'],
                ['goma_latest_client']),
        'chromeos-amd64-generic-rel-goma-latest':
            chromium_apply_configs(
                chromium_chromiumos.SPEC['builders']
                ['chromeos-amd64-generic-rel'], ['goma_latest_client']),
        # For building targets instrumented for code coverage.
        'linux-code-coverage':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'goma_high_parallel',
                ],
                gclient_config='chromium',
                gclient_apply_config=['use_clang_coverage'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER_TESTER,
                testing={
                    'platform': 'linux',
                },
            ),
        'Linux Builder Goma Latest Client':
            chromium_apply_configs(
                chromium_linux.SPEC['builders']['Linux Builder'],
                ['goma_latest_client', 'goma_use_local']),
        'linux-archive-rel-goma-latest':
            chromium_apply_configs(
                no_archive(chromium.SPEC['builders']['linux-archive-rel']),
                ['goma_latest_client']),
        'linux-archive-rel-goma-latest-localoutputcache':
            chromium_apply_configs(
                no_archive(chromium.SPEC['builders']['linux-archive-rel']),
                ['goma_latest_client', 'goma_localoutputcache']),
        # RBE
        'chromeos-amd64-generic-rel-goma-rbe-latest':
            chromium_apply_configs(
                chromium_chromiumos.SPEC['builders']
                ['chromeos-amd64-generic-rel'], ['goma_latest_client']),
        'Linux Builder Goma RBE Latest Client':
            chromium_apply_configs(
                chromium_linux.SPEC['builders']['Linux Builder'],
                ['goma_latest_client', 'goma_use_local']),
        'linux-archive-rel-goma-rbe-latest':
            chromium_apply_configs(
                no_archive(chromium.SPEC['builders']['linux-archive-rel']),
                ['goma_latest_client']),
        'linux-archive-rel-goma-rbe-ats-latest':
            chromium_apply_configs(
                no_archive(chromium.SPEC['builders']['linux-archive-rel']),
                ['goma_latest_client']),
        'Mac Builder Goma Latest Client':
            chromium_apply_configs(chromium_mac.SPEC['builders']['Mac Builder'],
                                   ['goma_latest_client', 'goma_use_local']),
        'Mac Builder (dbg) Goma Latest Client':
            chromium_apply_configs(
                chromium_mac.SPEC['builders']['Mac Builder (dbg)'],
                ['goma_latest_client']),
        'mac-archive-rel-goma-latest':
            chromium_apply_configs(
                no_archive(chromium.SPEC['builders']['mac-archive-rel']),
                ['goma_latest_client']),
        'Mac Builder (dbg) Goma Latest Client (clobber)':
            chromium_apply_configs(
                chromium_mac.SPEC['builders']['Mac Builder (dbg)'],
                ['goma_latest_client', 'clobber']),
        # Mac has less disks, so use small localoutputcache.
        # Build chrome only. Even with smaller localoutputcache, disk is short.
        # See crbug.com/825536
        'mac-archive-rel-goma-latest-localoutputcache':
            chromium_apply_configs(
                override_compile_targets(
                    no_archive(chromium.SPEC['builders']['mac-archive-rel']),
                    ['chrome']),
                ['goma_latest_client', 'goma_localoutputcache_small']),
        # RBE
        'Mac Builder (dbg) Goma RBE Latest Client (clobber)':
            chromium_apply_configs(
                chromium_mac.SPEC['builders']['Mac Builder (dbg)'],
                ['goma_latest_client', 'clobber']),
        'mac-archive-rel-goma-rbe-latest':
            chromium_apply_configs(
                no_archive(chromium.SPEC['builders']['mac-archive-rel']),
                ['goma_latest_client']),
        'mac-code-coverage':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                gclient_apply_config=['use_clang_coverage'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER_TESTER,
                testing={
                    'platform': 'mac',
                },
            ),
        'Win Builder (ANGLE)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                gclient_config='chromium',
                gclient_apply_config=['angle_top_of_tree'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                bot_type=bot_spec.BUILDER,
                test_results_config='staging_server',
                testing={
                    'platform': 'win',
                },
                patch_root='src/third_party/angle',
            ),
        'Win7 Tests (ANGLE)':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                gclient_config='chromium',
                gclient_apply_config=['angle_top_of_tree'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='Win Builder (ANGLE)',
                test_results_config='staging_server',
                testing={
                    'platform': 'win',
                },
            ),
        'win32-arm64-rel':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                gclient_config='chromium',
                chromium_apply_config=['mb'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_ARCH': 'arm'
                },
                bot_type=bot_spec.BUILDER,
                testing={
                    'platform': 'win',
                },
            ),

        # This builder no longer exists, but keep it around so that
        # Goma's canary bots can copy its config.
        'Android Builder (dbg)':
            bot_spec.BotSpec.create(
                chromium_config='android',
                chromium_apply_config=['mb', 'download_vr_test_apks'],
                gclient_config='chromium',
                gclient_apply_config=['android'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 32,
                    'TARGET_PLATFORM': 'android',
                },
                android_config='main_builder',
                bot_type=bot_spec.BUILDER,
                compile_targets=[
                    'chromedriver_webview_shell_apk',
                ],
                test_results_config='staging_server',
                testing={
                    'platform': 'linux',
                },
            ),
        'Win 10 Fast Ring':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                test_results_config='staging_server',
                testing={
                    'platform': 'win',
                },
            ),
        'Linux remote_run Builder':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER,
                test_results_config='staging_server',
                testing={
                    'platform': 'linux',
                },
            ),
        'Linux remote_run Tester':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                parent_buildername='Linux remote_run Builder',
                tests=[
                    steps.LocalGTestTest('base_unittests'),
                ],
                test_results_config='staging_server',
                testing={
                    'platform': 'linux',
                },
            ),
        'Mojo Android':
            bot_spec.BotSpec.create(
                chromium_config='android',
                chromium_apply_config=['android'],
                gclient_config='chromium',
                gclient_apply_config=['android'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'android',
                },
                bot_type=bot_spec.BUILDER_TESTER,
                android_config='arm64_builder_mb',
                # TODO(crbug.com/876570): Here and below, we should move the
                # Mojo builders to a different "master" and get rid of this
                # property; we don't really want different builders on the same
                # master to have different priorities, it makes reasoning about
                # builders harder for sheriffs and troopers.
                swarming_default_priority=25,
                testing={
                    'platform': 'linux',
                },
            ),
        'android-mojo-webview-rel':
            bot_spec.BotSpec.create(
                chromium_config='android',
                chromium_apply_config=['android'],
                gclient_config='chromium',
                gclient_apply_config=['android'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'android',
                },
                bot_type=bot_spec.BUILDER_TESTER,
                android_config='arm64_builder_mb',
                swarming_default_priority=25,
                testing={
                    'platform': 'linux',
                },
            ),
        'Mojo ChromiumOS':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                gclient_apply_config=['chromeos'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_PLATFORM': 'linux',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER_TESTER,
                swarming_default_priority=25,
                testing={
                    'platform': 'linux',
                },
            ),
        'Mojo Linux':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                swarming_default_priority=25,
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER_TESTER,
                testing={
                    'platform': 'linux',
                },
            ),
        'mac-mojo-rel':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                swarming_default_priority=25,
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER_TESTER,
                testing={
                    'platform': 'mac',
                },
            ),
        'Mojo Windows':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                swarming_default_priority=25,
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_PLATFORM': 'win',
                    'TARGET_BITS': 32,
                },
                bot_type=bot_spec.BUILDER_TESTER,
                testing={
                    'platform': 'win',
                },
            ),
        'chromeos-amd64-generic-rel-vm-tests':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                gclient_apply_config=['chromeos'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_ARCH': 'intel',
                    'TARGET_BITS': 64,
                    'TARGET_CROS_BOARD': 'amd64-generic',
                    'TARGET_PLATFORM': 'chromeos',
                },
                bot_type=bot_spec.BUILDER_TESTER,
                testing={
                    'platform': 'linux',
                },
                tests={},
            ),
        'chromeos-kevin-rel-hw-tests':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                ],
                gclient_config='chromium',
                gclient_apply_config=['chromeos'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 32,
                    'TARGET_CROS_BOARD': 'kevin',
                    'TARGET_PLATFORM': 'chromeos',
                },
                bot_type=bot_spec.BUILDER_TESTER,
                testing={
                    'platform': 'linux',
                },
                tests={},
            ),
        'linux-autofill-captured-sites-rel':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                gclient_config='chromium',
                chromium_apply_config=['mb'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'linux',
                },
                bot_type=bot_spec.BUILDER_TESTER,
                test_results_config='staging_server',
                testing={
                    'platform': 'linux',
                },
            ),
        'linux-chromeos-code-coverage':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'goma_high_parallel',
                ],
                gclient_config='chromium',
                gclient_apply_config=['chromeos', 'use_clang_coverage'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_ARCH': 'intel',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER_TESTER,
                testing={
                    'platform': 'linux',
                },
                tests={},
            ),
        'mac-autofill-captured-sites-rel':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                gclient_config='chromium',
                chromium_apply_config=['mb'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'mac',
                },
                bot_type=bot_spec.BUILDER_TESTER,
                compile_targets=[
                    'captured_sites_interactive_tests',
                ],
                test_results_config='staging_server',
                testing={
                    'platform': 'mac',
                },
            ),
        'win-autofill-captured-sites-rel':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                gclient_config='chromium',
                chromium_apply_config=['mb'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'win',
                },
                bot_type=bot_spec.BUILDER_TESTER,
                compile_targets=[
                    'captured_sites_interactive_tests',
                ],
                test_results_config='staging_server',
                testing={
                    'platform': 'win',
                },
            ),
        'ios-simulator-cr-recipe':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'mac_toolchain',
                ],
                chromium_tests_apply_config=[],
                gclient_config='ios',  # add 'ios' to target_os
                gclient_apply_config=[],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'ios',
                },
                testing={
                    'platform': 'mac',
                },
            ),
        'ios-simulator-code-coverage':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'ios_release_simulator',
                    'mac_toolchain',
                ],
                gclient_config='ios',
                gclient_apply_config=['use_clang_coverage'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'ios',
                },
                bot_type=bot_spec.BUILDER_TESTER,
                testing={
                    'platform': 'mac',
                },
            ),
        'android-code-coverage':
            bot_spec.BotSpec.create(
                chromium_config='android',
                chromium_apply_config=['download_vr_test_apks', 'mb'],
                gclient_config='chromium',
                gclient_apply_config=['android'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'android',
                },
                android_config='main_builder',
                bot_type=bot_spec.BUILDER_TESTER,
                testing={
                    'platform': 'linux',
                },
            ),
        'android-code-coverage-native':
            bot_spec.BotSpec.create(
                chromium_config='android',
                chromium_apply_config=['download_vr_test_apks', 'mb'],
                gclient_config='chromium',
                gclient_apply_config=['android', 'use_clang_coverage'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'android',
                },
                android_config='main_builder',
                bot_type=bot_spec.BUILDER_TESTER,
                testing={
                    'platform': 'linux',
                },
            ),
        'Win10 Tests x64 1803':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=['mb'],
                gclient_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.TESTER,
                tests=[],
                parent_mastername='chromium.win',
                parent_buildername='Win x64 Builder',
                testing={
                    'platform': 'win',
                },
            ),
        'win10-code-coverage':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_apply_config=[
                    'mb',
                    'goma_high_parallel',
                ],
                gclient_config='chromium',
                gclient_apply_config=['use_clang_coverage'],
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                bot_type=bot_spec.BUILDER_TESTER,
                testing={
                    'platform': 'win',
                },
            ),
    },
}

SPEC['builders']['android-archive-dbg-goma-canary'] = chromium_apply_configs(
    SPEC['builders']['Android Builder (dbg)'], ['goma_canary'])
SPEC['builders']['android-archive-dbg-goma-latest'] = (
    chromium_apply_configs(SPEC['builders']['Android Builder (dbg)'],
                           ['goma_latest_client']))

SPEC['builders']['android-archive-dbg-goma-rbe-canary'] = (
    chromium_apply_configs(SPEC['builders']['Android Builder (dbg)'],
                           ['goma_canary']))
SPEC['builders']['android-archive-dbg-goma-rbe-latest'] = (
    chromium_apply_configs(SPEC['builders']['Android Builder (dbg)'],
                           ['goma_latest_client']))

SPEC['builders']['android-archive-dbg-goma-rbe-ats-canary'] = (
    chromium_apply_configs(SPEC['builders']['Android Builder (dbg)'],
                           ['goma_canary']))
SPEC['builders']['android-archive-dbg-goma-rbe-ats-latest'] = (
    chromium_apply_configs(SPEC['builders']['Android Builder (dbg)'],
                           ['goma_latest_client']))

SPEC['builders'].update([
    stock_config('linux-blink-cors-rel'),
    stock_config('linux-blink-rel-dummy', staging=False),
    stock_config('mac10.10-blink-rel-dummy', staging=False),
    stock_config('mac10.11-blink-rel-dummy', staging=False),
    stock_config('mac10.12-blink-rel-dummy', staging=False),
    stock_config('mac10.13_retina-blink-rel-dummy', staging=False),
    stock_config('mac10.13-blink-rel-dummy', staging=False),
    stock_config('mac10.14-blink-rel-dummy', staging=False),
    stock_config('win7-blink-rel-dummy', target_bits=32, staging=False),
    stock_config('win10-blink-rel-dummy', target_bits=32, staging=False),
    stock_config('VR Linux'),
    stock_config('Linux Viz'),
    stock_config('linux-annotator-rel'),
    stock_config('linux-bfcache-debug', config='Debug'),
    stock_config('linux-blink-animation-use-time-delta', config='Debug'),
    stock_config('linux-blink-heap-concurrent-marking-tsan-rel'),
    stock_config('linux-blink-heap-verification'),
    stock_config(
        'linux-chromium-tests-staging-builder', bot_type=bot_spec.BUILDER),
    stock_config(
        'linux-chromium-tests-staging-tests',
        bot_type=bot_spec.TESTER,
        parent_buildername='linux-chromium-tests-staging-builder'),
    stock_config('linux-fieldtrial-rel'),
    stock_config('linux-gcc-rel'),
    stock_config('linux-tcmalloc-rel'),
    stock_config('linux-wpt-fyi-rel'),
    stock_config('mac-hermetic-upgrade-rel'),
    stock_config('win-annotator-rel'),
    stock_config('win-pixel-builder-rel', bot_type=bot_spec.BUILDER),
    stock_config(
        'win-pixel-tester-rel',
        bot_type=bot_spec.TESTER,
        parent_buildername='win-pixel-builder-rel'),
])
