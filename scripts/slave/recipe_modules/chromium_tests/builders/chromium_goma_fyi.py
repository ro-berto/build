# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_spec, steps
from . import chromium
from . import chromium_chromiumos
from . import chromium_linux
from . import chromium_mac
from . import chromium_win

RESULTS_URL = 'https://chromeperf.appspot.com'


def chromium_apply_configs(base_config, config_names):
  """chromium_apply_configs returns new config from base config with config.

  It adds config names in chromium_apply_config.

  Args:
    base_config: config obj in SPEC[x].
    config_names: a list of config names to be added into chromium_apply_config.
  Returns:
    new config obj.
  """
  return base_config.extend(chromium_apply_config=config_names)


def no_archive(base_config):
  """no_archive returns new config from base config without archive_build etc.

  Args:
    base_config: config obj in SPEC[x].
  Returns:
    new config obj.
  """
  return base_config.evolve(
      archive_build=None, gs_bucket=None, gs_acl=None, gs_build_name=None)


def override_compile_targets(base_config, compile_targets):
  """Overrides compile_targets.

  Args:
    base_config: config obj in SPEC[x].
    compile_targets: new compile targets.
  Returns:
    new config obj.
  """
  return base_config.evolve(compile_targets=compile_targets)


SPEC = {
    'Win Builder Goma Canary':
        chromium_apply_configs(chromium_win.SPEC['Win Builder'],
                               ['goma_canary', 'goma_use_local']),
    'Win Builder (dbg) Goma Canary':
        chromium_apply_configs(chromium_win.SPEC['Win Builder (dbg)'],
                               ['goma_canary']),
    'win32-archive-rel-goma-canary-localoutputcache':
        chromium_apply_configs(
            no_archive(chromium.SPEC['win-archive-rel']),
            ['goma_canary', 'goma_localoutputcache']),

    # TODO(b/139556893): remove after win7 builders removal.
    'Win7 Builder Goma Canary':
        chromium_apply_configs(chromium_win.SPEC['Win Builder'],
                               ['goma_canary']),
    'Win7 Builder (dbg) Goma Canary':
        chromium_apply_configs(chromium_win.SPEC['Win Builder (dbg)'],
                               ['goma_canary']),
    'chromeos-amd64-generic-rel-goma-canary':
        chromium_apply_configs(
            chromium_chromiumos.SPEC['chromeos-amd64-generic-rel'],
            ['goma_canary']),
    'Linux Builder Goma Canary':
        chromium_apply_configs(chromium_linux.SPEC['Linux Builder'],
                               ['goma_canary', 'goma_use_local']),
    'linux-archive-rel-goma-canary':
        chromium_apply_configs(
            no_archive(chromium.SPEC['linux-archive-rel']), ['goma_canary']),
    'linux-archive-rel-goma-canary-localoutputcache':
        chromium_apply_configs(
            no_archive(chromium.SPEC['linux-archive-rel']),
            ['goma_canary', 'goma_localoutputcache']),
    # RBE
    'chromeos-amd64-generic-rel-goma-rbe-canary':
        chromium_apply_configs(
            chromium_chromiumos.SPEC['chromeos-amd64-generic-rel'],
            ['goma_canary']),
    'Linux Builder Goma RBE Canary':
        chromium_apply_configs(chromium_linux.SPEC['Linux Builder'],
                               ['goma_canary', 'goma_use_local']),
    'linux-archive-rel-goma-rbe-canary':
        chromium_apply_configs(
            no_archive(chromium.SPEC['linux-archive-rel']), ['goma_canary']),
    'linux-archive-rel-goma-rbe-ats-canary':
        chromium_apply_configs(
            no_archive(chromium.SPEC['linux-archive-rel']), ['goma_canary']),
    'Mac Builder Goma Canary':
        chromium_apply_configs(chromium_mac.SPEC['Mac Builder'],
                               ['goma_canary', 'goma_use_local']),
    'Mac Builder (dbg) Goma Canary':
        chromium_apply_configs(chromium_mac.SPEC['Mac Builder (dbg)'],
                               ['goma_canary']),
    'mac-archive-rel-goma-canary':
        chromium_apply_configs(
            no_archive(chromium.SPEC['mac-archive-rel']), ['goma_canary']),
    'Mac Builder (dbg) Goma Canary (clobber)':
        chromium_apply_configs(chromium_mac.SPEC['Mac Builder (dbg)'],
                               ['goma_canary', 'clobber']),
    # Mac has less disks, so use small localoutputcache.
    # Build chrome only. Even with smaller localoutputcache, disk is short.
    # See crbug.com/825536
    'mac-archive-rel-goma-canary-localoutputcache':
        chromium_apply_configs(
            override_compile_targets(
                no_archive(chromium.SPEC['mac-archive-rel']), ['chrome']),
            ['goma_canary', 'goma_localoutputcache_small']),
    # RBE
    'mac-archive-rel-goma-rbe-canary':
        chromium_apply_configs(
            no_archive(chromium.SPEC['mac-archive-rel']), ['goma_canary']),
    'Mac Builder (dbg) Goma RBE Canary (clobber)':
        chromium_apply_configs(chromium_mac.SPEC['Mac Builder (dbg)'],
                               ['goma_canary', 'clobber']),

    # Latest Goma Client
    'Win Builder Goma Latest Client':
        chromium_apply_configs(chromium_win.SPEC['Win Builder'],
                               ['goma_latest_client', 'goma_use_local']),
    'Win Builder (dbg) Goma Latest Client':
        chromium_apply_configs(chromium_win.SPEC['Win Builder (dbg)'],
                               ['goma_latest_client']),
    'win32-archive-rel-goma-latest-localoutputcache':
        chromium_apply_configs(
            no_archive(chromium.SPEC['win-archive-rel']),
            ['goma_latest_client', 'goma_localoutputcache']),
    # RBE
    'Win Builder Goma RBE Latest Client':
        chromium_apply_configs(chromium_win.SPEC['Win Builder'],
                               ['goma_latest_client', 'goma_use_local']),
    'Win Builder (dbg) Goma RBE Latest Client':
        chromium_apply_configs(chromium_win.SPEC['Win Builder (dbg)'],
                               ['goma_latest_client']),

    # TODO(b/139556893): remove after removal of win7.
    'Win7 Builder Goma Latest Client':
        chromium_apply_configs(chromium_win.SPEC['Win Builder'],
                               ['goma_latest_client']),
    'Win7 Builder (dbg) Goma Latest Client':
        chromium_apply_configs(chromium_win.SPEC['Win Builder (dbg)'],
                               ['goma_latest_client']),
    'chromeos-amd64-generic-rel-goma-latest':
        chromium_apply_configs(
            chromium_chromiumos.SPEC['chromeos-amd64-generic-rel'],
            ['goma_latest_client']),
    'Linux Builder Goma Latest Client':
        chromium_apply_configs(chromium_linux.SPEC['Linux Builder'],
                               ['goma_latest_client', 'goma_use_local']),
    'linux-archive-rel-goma-latest':
        chromium_apply_configs(
            no_archive(chromium.SPEC['linux-archive-rel']),
            ['goma_latest_client']),
    'linux-archive-rel-goma-latest-localoutputcache':
        chromium_apply_configs(
            no_archive(chromium.SPEC['linux-archive-rel']),
            ['goma_latest_client', 'goma_localoutputcache']),
    # RBE
    'chromeos-amd64-generic-rel-goma-rbe-latest':
        chromium_apply_configs(
            chromium_chromiumos.SPEC['chromeos-amd64-generic-rel'],
            ['goma_latest_client']),
    'Linux Builder Goma RBE Latest Client':
        chromium_apply_configs(chromium_linux.SPEC['Linux Builder'],
                               ['goma_latest_client', 'goma_use_local']),
    'linux-archive-rel-goma-rbe-latest':
        chromium_apply_configs(
            no_archive(chromium.SPEC['linux-archive-rel']),
            ['goma_latest_client']),
    'linux-archive-rel-goma-rbe-ats-latest':
        chromium_apply_configs(
            no_archive(chromium.SPEC['linux-archive-rel']),
            ['goma_latest_client']),
    'Mac Builder Goma Latest Client':
        chromium_apply_configs(chromium_mac.SPEC['Mac Builder'],
                               ['goma_latest_client', 'goma_use_local']),
    'Mac Builder (dbg) Goma Latest Client':
        chromium_apply_configs(chromium_mac.SPEC['Mac Builder (dbg)'],
                               ['goma_latest_client']),
    'mac-archive-rel-goma-latest':
        chromium_apply_configs(
            no_archive(chromium.SPEC['mac-archive-rel']),
            ['goma_latest_client']),
    'Mac Builder (dbg) Goma Latest Client (clobber)':
        chromium_apply_configs(chromium_mac.SPEC['Mac Builder (dbg)'],
                               ['goma_latest_client', 'clobber']),
    # Mac has less disks, so use small localoutputcache.
    # Build chrome only. Even with smaller localoutputcache, disk is short.
    # See crbug.com/825536
    'mac-archive-rel-goma-latest-localoutputcache':
        chromium_apply_configs(
            override_compile_targets(
                no_archive(chromium.SPEC['mac-archive-rel']), ['chrome']),
            ['goma_latest_client', 'goma_localoutputcache_small']),
    # RBE
    'Mac Builder (dbg) Goma RBE Latest Client (clobber)':
        chromium_apply_configs(chromium_mac.SPEC['Mac Builder (dbg)'],
                               ['goma_latest_client', 'clobber']),
    'mac-archive-rel-goma-rbe-latest':
        chromium_apply_configs(
            no_archive(chromium.SPEC['mac-archive-rel']),
            ['goma_latest_client']),
    # This builder no longer exists, but keep it around so that
    # Goma's canary bots can copy its config.
    'Android Builder (dbg)':
        bot_spec.BotSpec.create(
            chromium_config='android',
            chromium_apply_config=[
                'mb', 'mb_luci_auth', 'download_vr_test_apks'
            ],
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
            simulation_platform='linux',
        ),
    'ios-device-goma-canary-clobber':
        chromium_apply_configs(chromium_mac.SPEC['ios-device'],
                               ['goma_canary', 'clobber']),
    'ios-device-goma-latest-clobber':
        chromium_apply_configs(chromium_mac.SPEC['ios-device'],
                               ['goma_latest_client', 'clobber']),
    'ios-device-goma-rbe-canary-clobber':
        chromium_apply_configs(chromium_mac.SPEC['ios-device'],
                               ['goma_canary', 'clobber']),
    'ios-device-goma-rbe-latest-clobber':
        chromium_apply_configs(chromium_mac.SPEC['ios-device'],
                               ['goma_latest_client', 'clobber']),
}

SPEC['android-archive-dbg-goma-canary'] = chromium_apply_configs(
    SPEC['Android Builder (dbg)'], ['goma_canary'])
SPEC['android-archive-dbg-goma-latest'] = (
    chromium_apply_configs(SPEC['Android Builder (dbg)'],
                           ['goma_latest_client']))

SPEC['android-archive-dbg-goma-rbe-canary'] = (
    chromium_apply_configs(SPEC['Android Builder (dbg)'], ['goma_canary']))
SPEC['android-archive-dbg-goma-rbe-latest'] = (
    chromium_apply_configs(SPEC['Android Builder (dbg)'],
                           ['goma_latest_client']))

SPEC['android-archive-dbg-goma-rbe-ats-canary'] = (
    chromium_apply_configs(SPEC['Android Builder (dbg)'], ['goma_canary']))
SPEC['android-archive-dbg-goma-rbe-ats-latest'] = (
    chromium_apply_configs(SPEC['Android Builder (dbg)'],
                           ['goma_latest_client']))

# Many of the FYI specs are made by transforming specs from other files, so
# rather than have to do 2 different things for specs based on other specs and
# specs created within this file, just evolve all of the specs afterwards
for name, spec in SPEC.iteritems():
  SPEC[name] = spec.evolve(build_gs_bucket='chromium-fyi-archive')
