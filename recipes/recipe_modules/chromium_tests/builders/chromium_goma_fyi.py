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


SPEC = {
    # Canary RBE
    'linux-archive-rel-goma-rbe-canary':
        chromium_apply_configs(
            no_archive(chromium.SPEC['linux-archive-rel']), ['goma_canary']),
    'linux-archive-rel-goma-rbe-ats-canary':
        chromium_apply_configs(
            no_archive(chromium.SPEC['linux-archive-rel']), ['goma_canary']),
    'Linux Builder Goma RBE Canary':
        chromium_apply_configs(chromium_linux.SPEC['Linux Builder'],
                               ['goma_canary', 'goma_use_local']),
    'chromeos-amd64-generic-rel-goma-rbe-canary':
        chromium_apply_configs(
            chromium_chromiumos.SPEC['chromeos-amd64-generic-rel'],
            ['goma_canary']),
    'mac-archive-rel-goma-rbe-canary':
        chromium_apply_configs(
            no_archive(chromium.SPEC['mac-archive-rel']), ['goma_canary']),
    'Mac Builder (dbg) Goma RBE Canary (clobber)':
        chromium_apply_configs(chromium_mac.SPEC['Mac Builder (dbg)'],
                               ['goma_canary', 'clobber']),
    'ios-device-goma-rbe-canary-clobber':
        chromium_apply_configs(chromium_mac.SPEC['ios-device'],
                               ['goma_canary', 'clobber']),
    'Win Builder Goma RBE Canary':
        chromium_apply_configs(chromium_win.SPEC['Win Builder'],
                               ['goma_canary', 'goma_use_local']),
    'Win Builder (dbg) Goma RBE Canary':
        chromium_apply_configs(chromium_win.SPEC['Win Builder (dbg)'],
                               ['goma_canary']),
    'Win Builder Goma RBE ATS Canary':
        chromium_apply_configs(chromium_win.SPEC['Win Builder'],
                               ['goma_canary', 'goma_use_local']),
    'Win Builder (dbg) Goma RBE ATS Canary':
        chromium_apply_configs(chromium_win.SPEC['Win Builder (dbg)'],
                               ['goma_canary']),

    # Latest RBE
    'linux-archive-rel-goma-rbe-latest':
        chromium_apply_configs(
            no_archive(chromium.SPEC['linux-archive-rel']),
            ['goma_latest_client']),
    'linux-archive-rel-goma-rbe-ats-latest':
        chromium_apply_configs(
            no_archive(chromium.SPEC['linux-archive-rel']),
            ['goma_latest_client']),
    'Linux Builder Goma RBE Latest Client':
        chromium_apply_configs(chromium_linux.SPEC['Linux Builder'],
                               ['goma_latest_client', 'goma_use_local']),
    'chromeos-amd64-generic-rel-goma-rbe-latest':
        chromium_apply_configs(
            chromium_chromiumos.SPEC['chromeos-amd64-generic-rel'],
            ['goma_latest_client']),
    'mac-archive-rel-goma-rbe-latest':
        chromium_apply_configs(
            no_archive(chromium.SPEC['mac-archive-rel']),
            ['goma_latest_client']),
    'Mac Builder (dbg) Goma RBE Latest Client (clobber)':
        chromium_apply_configs(chromium_mac.SPEC['Mac Builder (dbg)'],
                               ['goma_latest_client', 'clobber']),
    'ios-device-goma-rbe-latest-clobber':
        chromium_apply_configs(chromium_mac.SPEC['ios-device'],
                               ['goma_latest_client', 'clobber']),
    'Win Builder Goma RBE Latest Client':
        chromium_apply_configs(chromium_win.SPEC['Win Builder'],
                               ['goma_latest_client', 'goma_use_local']),
    'Win Builder (dbg) Goma RBE Latest Client':
        chromium_apply_configs(chromium_win.SPEC['Win Builder (dbg)'],
                               ['goma_latest_client']),

    # This builder no longer exists, but keep it around so that
    # Goma's canary bots can copy its config.
    'Android Builder (dbg)':
        bot_spec.BotSpec.create(
            chromium_config='android',
            chromium_apply_config=['mb', 'download_vr_test_apks'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            test_results_config='staging_server',
            simulation_platform='linux',
        ),
}

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
