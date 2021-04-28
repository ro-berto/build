# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec

RESULTS_URL = 'https://chromeperf.appspot.com'


def _chromium_android_spec(**kwargs):
  return builder_spec.BuilderSpec.create(
      build_gs_bucket='chromium-android-archive', **kwargs)


SPEC = {
    'Android arm Builder (dbg)':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder_mb',
            simulation_platform='linux',
        ),
    'Android arm64 Builder (dbg)':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder_mb',
            simulation_platform='linux',
        ),
    'Android ASAN (dbg)':
        _chromium_android_spec(
            chromium_config='android_clang',
            chromium_apply_config=[
                'errorprone',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='clang_builder_mb',
            simulation_platform='linux',
        ),
    'Android x64 Builder (dbg)':
        _chromium_android_spec(
            chromium_config='android',
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='x64_builder_mb',
            simulation_platform='linux',
        ),
    'Android x86 Builder (dbg)':
        _chromium_android_spec(
            chromium_config='android',
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='x86_builder_mb',
            simulation_platform='linux',
        ),
    'Cast Android (dbg)':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'mb',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='cast_builder',
            simulation_platform='linux',
        ),
    'Marshmallow 64 bit Tester':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android', 'enable_wpr_tests'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm64 Builder (dbg)',
            execution_mode=builder_spec.TEST,
            android_config='main_builder_mb',
            simulation_platform='linux',
        ),
    'Lollipop Phone Tester':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm Builder (dbg)',
            execution_mode=builder_spec.TEST,
            android_config='main_builder_mb',
            simulation_platform='linux',
        ),
    'Lollipop Tablet Tester':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm Builder (dbg)',
            execution_mode=builder_spec.TEST,
            android_config='main_builder_mb',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Marshmallow Phone Tester (rel)':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder_mb',
            simulation_platform='linux',
        ),
    'Marshmallow Tablet Tester':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm Builder (dbg)',
            execution_mode=builder_spec.TEST,
            android_config='main_builder_mb',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Nougat Phone Tester':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm64 Builder (dbg)',
            execution_mode=builder_spec.TEST,
            android_config='main_builder_mb',
            simulation_platform='linux',
        ),
    'Oreo Phone Tester':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm64 Builder (dbg)',
            execution_mode=builder_spec.TEST,
            android_config='main_builder_mb',
            simulation_platform='linux',
        ),
    'android-pie-arm64-dbg':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm64 Builder (dbg)',
            execution_mode=builder_spec.TEST,
            android_config='main_builder_mb',
            simulation_platform='linux',
        ),
    'Android WebView L (dbg)':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm Builder (dbg)',
            execution_mode=builder_spec.TEST,
            android_config='main_builder_mb',
            simulation_platform='linux',
        ),
    'Android WebView M (dbg)':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm64 Builder (dbg)',
            execution_mode=builder_spec.TEST,
            android_config='main_builder_mb',
            android_apply_config=['remove_all_system_webviews'],
            simulation_platform='linux',
        ),
    'Android WebView N (dbg)':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm64 Builder (dbg)',
            execution_mode=builder_spec.TEST,
            android_config='main_builder_mb',
            android_apply_config=['remove_all_system_webviews'],
            simulation_platform='linux',
        ),
    'Android WebView O (dbg)':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm64 Builder (dbg)',
            execution_mode=builder_spec.TEST,
            android_config='main_builder_mb',
            android_apply_config=['remove_all_system_webviews'],
            simulation_platform='linux',
        ),
    'Android WebView P (dbg)':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            isolate_server='https://isolateserver.appspot.com',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm64 Builder (dbg)',
            execution_mode=builder_spec.TEST,
            android_config='main_builder_mb',
            android_apply_config=['remove_all_system_webviews'],
            simulation_platform='linux',
        ),
    'android-weblayer-with-aosp-webview-x86-rel':
        _chromium_android_spec(
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
    'android-weblayer-x86-rel':
        _chromium_android_spec(
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
    'android-weblayer-marshmallow-x86-rel-tests':
        _chromium_android_spec(
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
            parent_buildername='android-weblayer-with-aosp-webview-x86-rel',
            execution_mode=builder_spec.TEST,
            android_config='x86_builder',
            simulation_platform='linux',
        ),
    'android-weblayer-oreo-x86-rel-tests':
        _chromium_android_spec(
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
            parent_buildername='android-weblayer-x86-rel',
            execution_mode=builder_spec.TEST,
            android_config='x86_builder',
            simulation_platform='linux',
        ),
    'android-weblayer-pie-x86-rel-tests':
        _chromium_android_spec(
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
            parent_buildername='android-weblayer-x86-rel',
            execution_mode=builder_spec.TEST,
            android_config='x86_builder',
            simulation_platform='linux',
        ),
}


def stock_config(name,
                 config='Release',
                 chromium_apply_config=None,
                 chromium_config_kwargs=None,
                 **kwargs):
  bot_config = {
      'chromium_config': 'android',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
          'BUILD_CONFIG': config,
          'TARGET_BITS': 32,
          'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder',
      'execution_mode': builder_spec.COMPILE_AND_TEST,
      'simulation_platform': 'linux',
  }

  if chromium_apply_config:
    bot_config['chromium_apply_config'].extend(chromium_apply_config)
    bot_config['chromium_apply_config'].sort()
  if chromium_config_kwargs:
    bot_config['chromium_config_kwargs'].update(chromium_config_kwargs)
  bot_config.update(**kwargs)
  return name, _chromium_android_spec(**bot_config)


def stock_cronet_config(name, config='Release', **kwargs):
  return stock_config(
      name,
      config=config,
      chromium_apply_config=['cronet_builder'],
      isolate_server='https://isolateserver.appspot.com',
      **kwargs)


SPEC.update([
    stock_config(
        'android-arm64-proguard-rel',
        chromium_apply_config=['download_vr_test_apks'],
        isolate_server='https://isolateserver.appspot.com',
        chromium_config_kwargs={'TARGET_BITS': 64}),
    stock_config(
        'android-bfcache-rel',
        chromium_apply_config=['download_vr_test_apks'],
        isolate_server='https://isolateserver.appspot.com',
        chromium_config_kwargs={'TARGET_BITS': 32}),
    stock_config(
        'android-incremental-dbg',
        isolate_server='https://isolateserver.appspot.com',
        config='Debug'),
    stock_config(
        'android-lollipop-arm-rel',
        chromium_apply_config=['download_vr_test_apks'],
        isolate_server='https://isolateserver.appspot.com',
        chromium_config_kwargs={'TARGET_BITS': 32}),
    stock_config(
        'android-marshmallow-arm64-rel',
        chromium_apply_config=[
            'download_vr_test_apks',
        ],
        isolate_server='https://isolateserver.appspot.com',
        chromium_config_kwargs={'TARGET_BITS': 64}),
    stock_config(
        'android-marshmallow-x86-rel',
        isolate_server='https://isolateserver.appspot.com',
        gclient_apply_config=['android', 'enable_wpr_tests'],
        android_config='x86_builder'),
    stock_config(
        'android-marshmallow-x86-rel-non-cq',
        isolate_server='https://isolateserver.appspot.com',
        gclient_apply_config=['android', 'enable_wpr_tests'],
        android_config='x86_builder'),
    stock_config(
        'android-nougat-arm64-rel',
        chromium_apply_config=['download_vr_test_apks'],
        isolate_server='https://isolateserver.appspot.com',
        chromium_config_kwargs={'TARGET_BITS': 64}),
    stock_config(
        'android-pie-arm64-coverage-experimental-rel',
        isolate_server='https://isolateserver.appspot.com',
        gclient_apply_config=['android', 'use_clang_coverage'],
        chromium_config_kwargs={'TARGET_BITS': 64}),
    stock_config(
        'android-pie-arm64-rel',
        isolate_server='https://isolateserver.appspot.com',
        chromium_config_kwargs={'TARGET_BITS': 64}),
    stock_config(
        'android-pie-arm64-wpt-rel-non-cq',
        isolate_server='https://isolateserver.appspot.com',
        chromium_config_kwargs={'TARGET_BITS': 64}),
    stock_config(
        'android-pie-x86-rel',
        isolate_server='https://isolateserver.appspot.com',
        android_config='x86_builder'),
    stock_config(
        'android-10-arm64-rel',
        chromium_apply_config=['download_vr_test_apks'],
        isolate_server='https://isolateserver.appspot.com',
        gclient_apply_config=['android', 'enable_wpr_tests'],
        chromium_config_kwargs={'TARGET_BITS': 64}),
    stock_cronet_config('android-cronet-arm-dbg', config='Debug'),
    stock_cronet_config('android-cronet-arm-rel'),
    stock_cronet_config('android-cronet-arm64-dbg', config='Debug'),
    stock_cronet_config('android-cronet-arm64-rel'),
    stock_cronet_config('android-cronet-asan-arm-rel'),
    stock_cronet_config(
        'android-cronet-arm-rel-kitkat-tests',
        execution_mode=builder_spec.TEST,
        parent_buildername='android-cronet-arm-rel'),
    stock_cronet_config(
        'android-cronet-arm-rel-lollipop-tests',
        execution_mode=builder_spec.TEST,
        parent_buildername='android-cronet-arm-rel'),
    stock_cronet_config(
        'android-cronet-arm64-rel-marshmallow-tests',
        execution_mode=builder_spec.TEST,
        parent_buildername='android-cronet-arm64-rel'),
    stock_cronet_config('android-cronet-x86-dbg', config='Debug'),
    stock_cronet_config('android-cronet-x86-rel'),
])
