# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import six

from .. import builder_spec
from . import chromium
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


# The config for the following builders is now specified src-side in
# //infra/config/subprojects/goma/goma.star
# * Linux Builder Goma RBE Canary
# * Linux Builder Goma RBE Latest Client
# * Mac Builder (dbg) Goma RBE Canary (clobber)
# * Mac Builder (dbg) Goma RBE Latest Client (clobber)
# * Mac M1 Builder (dbg) Goma RBE Canary (clobber)
# * chromeos-amd64-generic-rel-goma-rbe-canary
# * chromeos-amd64-generic-rel-goma-rbe-latest

SPEC = {
    # Canary RBE
    'linux-archive-rel-goma-rbe-canary':
        chromium_apply_configs(chromium.SPEC['linux-archive-rel'],
                               ['goma_canary']),
    'linux-archive-rel-goma-rbe-ats-canary':
        chromium_apply_configs(chromium.SPEC['linux-archive-rel'],
                               ['goma_canary']),
    'mac-archive-rel-goma-rbe-canary':
        chromium_apply_configs(chromium.SPEC['mac-archive-rel'],
                               ['goma_canary']),
    'ios-device-goma-rbe-canary-clobber':
        chromium_apply_configs(chromium_mac.SPEC['ios-device'],
                               ['goma_canary', 'clobber']),
    'mac-m1-archive-rel-goma-rbe-canary':
        chromium_apply_configs(chromium.SPEC['mac-archive-rel'],
                               ['goma_canary']),
    'Win Builder Goma RBE Canary':
        chromium_apply_configs(chromium_win.SPEC['Win Builder'],
                               ['goma_canary', 'goma_use_local']),
    'Win Builder Goma RBE Canary (clobber)':
        chromium_apply_configs(chromium_win.SPEC['Win Builder'],
                               ['goma_canary', 'goma_use_local', 'clobber']),
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
        chromium_apply_configs(chromium.SPEC['linux-archive-rel'],
                               ['goma_latest_client']),
    'linux-archive-rel-goma-rbe-ats-latest':
        chromium_apply_configs(chromium.SPEC['linux-archive-rel'],
                               ['goma_latest_client']),
    'mac-archive-rel-goma-rbe-latest':
        chromium_apply_configs(chromium.SPEC['mac-archive-rel'],
                               ['goma_latest_client']),
    'ios-device-goma-rbe-latest-clobber':
        chromium_apply_configs(chromium_mac.SPEC['ios-device'],
                               ['goma_latest_client', 'clobber']),
    'Win Builder Goma RBE Latest Client':
        chromium_apply_configs(chromium_win.SPEC['Win Builder'],
                               ['goma_latest_client', 'goma_use_local']),
    'Win Builder (dbg) Goma RBE Latest Client':
        chromium_apply_configs(chromium_win.SPEC['Win Builder (dbg)'],
                               ['goma_latest_client']),
    'Win Builder Goma RBE ATS Latest Client':
        chromium_apply_configs(chromium_win.SPEC['Win Builder'],
                               ['goma_latest_client', 'goma_use_local']),
    'Win Builder (dbg) Goma RBE ATS Latest Client':
        chromium_apply_configs(chromium_win.SPEC['Win Builder (dbg)'],
                               ['goma_latest_client']),

    # This builder no longer exists, but keep it around so that
    # Goma's canary bots can copy its config.
    'Android Builder (dbg)':
        builder_spec.BuilderSpec.create(
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
for name, spec in six.iteritems(SPEC):
  SPEC[name] = spec.evolve(build_gs_bucket='chromium-fyi-archive')
