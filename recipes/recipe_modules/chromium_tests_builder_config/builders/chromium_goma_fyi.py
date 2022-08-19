# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec

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
# * Win Builder (dbg) Goma RBE ATS Canary
# * Win Builder (dbg) Goma RBE ATS Latest Client
# * Win Builder (dbg) Goma RBE Canary
# * Win Builder (dbg) Goma RBE Latest Client
# * Win Builder Goma RBE ATS Canary
# * Win Builder Goma RBE ATS Latest Client
# * Win Builder Goma RBE Canary
# * Win Builder Goma RBE Canary (clobber)
# * Win Builder Goma RBE Latest Client
# * chromeos-amd64-generic-rel-goma-rbe-canary
# * chromeos-amd64-generic-rel-goma-rbe-latest
# * ios-device-goma-rbe-canary-clobber
# * ios-device-goma-rbe-latest-clobber
# * linux-archive-rel-goma-rbe-ats-canary
# * linux-archive-rel-goma-rbe-ats-latest
# * linux-archive-rel-goma-rbe-canary
# * linux-archive-rel-goma-rbe-latest
# * mac-archive-rel-goma-rbe-canary
# * mac-archive-rel-goma-rbe-latest

SPEC = {
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
for name, spec in SPEC.items():
  SPEC[name] = spec.evolve(build_gs_bucket='chromium-fyi-archive')
