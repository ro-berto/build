# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_spec

RESULTS_URL = 'https://chromeperf.appspot.com'


def _chromium_android_fyi_spec(**kwargs):
  return bot_spec.BotSpec.create(
      build_gs_bucket='chromium-android-archive', **kwargs)


SPEC = {
    'Android WebView P FYI (rel)':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
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
    'android-weblayer-x86-fyi-rel':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
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
    'Memory Infra Tester':
        _chromium_android_fyi_spec(
            chromium_config='android',
            isolate_server='https://isolateserver.appspot.com',
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
    'android-11-x86-fyi-rel':
        _chromium_android_fyi_spec(
            chromium_config='android',
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='x86_builder_mb',
            simulation_platform='linux',
        ),
    'android-inverse-fieldtrials-pie-x86-fyi-rel':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
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
    'android-pie-arm64-fyi-rel':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
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
    'android-pie-arm64-wpt-rel-non-cq':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
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
    'android-pie-x86-fyi-rel':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
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
    'android-weblayer-x86-fyi-rel-10-tests':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='android-weblayer-x86-fyi-rel',
            execution_mode=bot_spec.TEST,
            android_config='x86_builder',
            simulation_platform='linux',
        ),
    'android-weblayer-10-x86-rel-tests':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='android-weblayer-x86-fyi-rel',
            execution_mode=bot_spec.TEST,
            android_config='x86_builder',
            simulation_platform='linux',
        ),
    'android-weblayer-marshmallow-x86-rel-tests':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='android-weblayer-x86-fyi-rel',
            execution_mode=bot_spec.TEST,
            android_config='x86_builder',
            simulation_platform='linux',
        ),
    'android-weblayer-lollipop-x86-rel-tests':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='android-weblayer-x86-fyi-rel',
            execution_mode=bot_spec.TEST,
            android_config='x86_builder',
            simulation_platform='linux',
        ),
    'android-weblayer-oreo-x86-rel-tests':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='android-weblayer-x86-fyi-rel',
            execution_mode=bot_spec.TEST,
            android_config='x86_builder',
            simulation_platform='linux',
        ),
    'android-weblayer-pie-x86-rel-tests':
        _chromium_android_fyi_spec(
            chromium_config='android',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='android-weblayer-x86-fyi-rel',
            execution_mode=bot_spec.TEST,
            android_config='x86_builder',
            simulation_platform='linux',
        ),
}
