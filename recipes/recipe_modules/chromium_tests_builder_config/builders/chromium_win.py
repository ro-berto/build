# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec


def _chromium_win_spec(**kwargs):
  return builder_spec.BuilderSpec.create(
      build_gs_bucket='chromium-win-archive', **kwargs)

# The config for the following builders is now specified src-side in
# //infra/config/subprojects/chromium/ci/chromium.win.star
# * Win 7 Tests x64 (1)
# * Win Builder (dbg)
# * Win x64 Builder
# * Win x64 Builder (dbg)
# * Win10 Tests x64
# * Win10 Tests x64 (dbg)

SPEC = {
    'WebKit Win10':
        _chromium_win_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'goma_enable_global_file_stat_cache',
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='Win Builder',
            simulation_platform='win',
        ),
    'Win Builder':
        _chromium_win_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'goma_enable_global_file_stat_cache',
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            simulation_platform='win',
        ),
    'Win7 (32) Tests':
        _chromium_win_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'goma_enable_global_file_stat_cache',
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='Win Builder',
            simulation_platform='win',
        ),
    'Win7 Tests (1)':
        _chromium_win_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'goma_enable_global_file_stat_cache',
                'mb',
            ],
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='Win Builder',
            simulation_platform='win',
        ),
}
