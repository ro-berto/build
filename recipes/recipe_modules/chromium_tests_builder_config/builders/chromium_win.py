# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec


def _chromium_win_spec(**kwargs):
  return builder_spec.BuilderSpec.create(
      build_gs_bucket='chromium-win-archive', **kwargs)


SPEC = {
    'WebKit Win10':
        _chromium_win_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'goma_enable_global_file_stat_cache',
                'mb',
            ],
            isolate_server='https://isolateserver.appspot.com',
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
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            simulation_platform='win',
        ),
    'Win10 Tests x64':
        _chromium_win_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['use_clang_coverage'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'win',
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='Win x64 Builder',
            simulation_platform='win',
        ),
    'Win7 (32) Tests':
        _chromium_win_spec(
            chromium_config='chromium',
            chromium_apply_config=[
                'goma_enable_global_file_stat_cache',
                'mb',
            ],
            isolate_server='https://isolateserver.appspot.com',
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
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='Win Builder',
            simulation_platform='win',
        ),
    'Win x64 Builder':
        _chromium_win_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['use_clang_coverage'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'win',
            },
            simulation_platform='win',
        ),
    'Win 7 Tests x64 (1)':
        _chromium_win_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'win',
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='Win x64 Builder',
            simulation_platform='win',
        ),
    'Win x64 Builder (dbg)':
        _chromium_win_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            simulation_platform='win',
        ),
    'Win Builder (dbg)':
        _chromium_win_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
            },
            simulation_platform='win',
        ),
    'Win7 Tests (dbg)(1)':
        _chromium_win_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            isolate_server='https://isolateserver.appspot.com',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='Win Builder (dbg)',
            simulation_platform='win',
        ),
    'Win10 Tests x64 (dbg)':
        _chromium_win_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            },
            execution_mode=builder_spec.TEST,
            parent_buildername='Win x64 Builder (dbg)',
            simulation_platform='win',
        ),
}
