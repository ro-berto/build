# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec

RESULTS_URL = 'https://chromeperf.appspot.com'


def _chromium_android_fyi_spec(**kwargs):
  return builder_spec.BuilderSpec.create(
      build_gs_bucket='chromium-android-archive', **kwargs)


SPEC = {
    'Android arm64 Builder (dbg) (reclient)':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'android',
                'enable_reclient',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder_mb',
            simulation_platform='linux',
        ),
    'Android ASAN (dbg) (reclient)':
        _chromium_android_fyi_spec(
            chromium_config='android_clang',
            chromium_apply_config=[
                'errorprone',
            ],
            gclient_config='chromium',
            gclient_apply_config=[
                'android',
                'enable_reclient',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='clang_builder_mb',
            simulation_platform='linux',
        ),
    'Android WebView P FYI (rel)':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=[
                'android',
                'enable_reclient',
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            simulation_platform='linux',
        ),
    'android-weblayer-with-aosp-webview-x86-fyi-rel':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['android', 'enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='x86_builder',
            simulation_platform='linux',
        ),
    'Memory Infra Tester':
        _chromium_android_fyi_spec(
            chromium_config='android',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder_mb',
            simulation_platform='linux',
        ),
    'android-10-x86-fyi-rel-tests':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='android-x86-fyi-rel',
            execution_mode=builder_spec.TEST,
            android_config='x86_builder',
            simulation_platform='linux',
        ),
    'android-11-x86-fyi-rel':
        _chromium_android_fyi_spec(
            chromium_config='android',
            gclient_config='chromium',
            gclient_apply_config=['android', 'enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='x86_builder_mb',
            simulation_platform='linux',
        ),
    'android-12-x64-dbg-tests':
        _chromium_android_fyi_spec(
            chromium_config='android',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            parent_builder_group='chromium.android',
            parent_buildername='Android x64 Builder (dbg)',
            execution_mode=builder_spec.TEST,
            android_config='x64_builder_mb',
            simulation_platform='linux',
        ),
    # TODO(crbug.com/1225851): Remote FYI config after
    # android-12-x64-rel is  up and running.
    'android-12-x64-fyi-rel':
        _chromium_android_fyi_spec(
            chromium_config='android',
            gclient_config='chromium',
            gclient_apply_config=['android', 'enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='x64_builder_mb',
            simulation_platform='linux',
        ),
    'android-chrome-pie-x86-wpt-fyi-rel':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['android', 'enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='x86_builder',
            simulation_platform='linux',
        ),
    'android-marshmallow-x86-fyi-rel-reviver':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=[
                'android', 'enable_wpr_tests', 'enable_reclient'
            ],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='x86_builder',
            execution_mode=builder_spec.COMPILE_AND_TEST,
            simulation_platform='linux',
        ),
    'android-pie-arm64-fyi-rel':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            simulation_platform='linux',
        ),
    'android-weblayer-pie-x86-wpt-fyi-rel':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['android', 'enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='x86_builder',
            simulation_platform='linux',
        ),
    'android-weblayer-pie-x86-wpt-smoketest':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['android', 'enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='x86_builder',
            simulation_platform='linux',
        ),
    'android-webview-12-x64-dbg-tests':
        _chromium_android_fyi_spec(
            chromium_config='android',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            parent_builder_group='chromium.android',
            parent_buildername='Android x64 Builder (dbg)',
            execution_mode=builder_spec.TEST,
            android_config='x64_builder_mb',
            simulation_platform='linux',
        ),
    'android-webview-pie-x86-wpt-fyi-rel':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['android', 'enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='x86_builder',
            simulation_platform='linux',
        ),
    'android-pie-arm64-wpt-rel-non-cq':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['android', 'enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            simulation_platform='linux',
        ),
    'android-pie-x86-fyi-rel':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='x86_builder',
            simulation_platform='linux',
        ),
    'android-weblayer-10-x86-rel-tests':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='android-weblayer-with-aosp-webview-x86-fyi-rel',
            execution_mode=builder_spec.TEST,
            android_config='x86_builder',
            simulation_platform='linux',
        ),
    'android-weblayer-11-x86-rel-tests':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='android-weblayer-with-aosp-webview-x86-fyi-rel',
            execution_mode=builder_spec.TEST,
            android_config='x86_builder',
            simulation_platform='linux',
        ),
    'android-x86-fyi-rel':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['android', 'enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='x86_builder',
            simulation_platform='linux',
        ),
    'android-annotator-rel':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['android', 'enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            simulation_platform='linux',
        ),
}
