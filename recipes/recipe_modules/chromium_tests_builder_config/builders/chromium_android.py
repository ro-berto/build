# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec

RESULTS_URL = 'https://chromeperf.appspot.com'


def _chromium_android_spec(**kwargs):
  return builder_spec.BuilderSpec.create(
      build_gs_bucket='chromium-android-archive', **kwargs)


# The config for the following builders is now specified src-side in
# //infra/config/subprojects/chromium/ci/chromium.android.star
# * Android arm Builder (dbg)
# * Android arm64 Builder (dbg)
# * Android ASAN (dbg)
# * Android x64 Builder (dbg)
# * Android WebView M (dbg)
# * Android WebView N (dbg)
# * Android WebView O (dbg)
# * Android WebView P (dbg)
# * Marshmallow Tablet Tester
# * Marshmallow 64 bit Tester
# * Nougat Phone Tester
# * Oreo Phone Tester
# * android-12-x64-rel
# * android-arm64-proguard-rel
# * android-bfcache-rel
# * android-cronet-arm-dbg
# * android-cronet-x86-dbg
# * android-cronet-x86-dbg-10-tests
# * android-cronet-x86-dbg-11-tests
# * android-cronet-x86-dbg-lollipop-tests
# * android-cronet-x86-dbg-marshmallow-tests
# * android-cronet-x86-dbg-oreo-tests
# * android-cronet-x86-dbg-pie-tests
# * android-marshmallow-arm64-rel
# * android-marshmallow-x86-rel-non-cq
# * android-pie-arm64-dbg
# * android-weblayer-10-x86-rel-tests
# * android-weblayer-marshmallow-x86-rel-tests
# * android-weblayer-oreo-x86-rel-tests
# * android-weblayer-pie-x86-rel-tests
# * android-weblayer-with-aosp-webview-x86-rel
# * android-weblayer-x86-rel

SPEC = {
    'Android x86 Builder (dbg)':
        _chromium_android_spec(
            chromium_config='android',
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
            android_config='x86_builder_mb',
            simulation_platform='linux',
        ),
    'Cast Android (dbg)':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'mb',
            ],
            gclient_config='chromium',
            gclient_apply_config=['android', 'enable_reclient'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='cast_builder',
            simulation_platform='linux',
        ),
    'Marshmallow Phone Tester (rel)':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
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
      'gclient_apply_config': ['android', 'enable_reclient'],
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
      gclient_apply_config=['android', 'enable_reclient'],
      **kwargs)


SPEC.update([
    stock_config('android-incremental-dbg', config='Debug'),
    stock_config(
        'android-lollipop-arm-rel',
        chromium_apply_config=['download_vr_test_apks'],
        chromium_config_kwargs={'TARGET_BITS': 32}),
    stock_config(
        'android-marshmallow-x86-rel',
        gclient_apply_config=['android', 'enable_wpr_tests', 'enable_reclient'],
        android_config='x86_builder'),
    stock_config(
        'android-nougat-arm64-rel',
        chromium_apply_config=['download_vr_test_apks'],
        chromium_config_kwargs={'TARGET_BITS': 64}),
    stock_config(
        'android-pie-arm64-coverage-experimental-rel',
        gclient_apply_config=[
            'android', 'use_clang_coverage', 'enable_reclient'
        ],
        chromium_config_kwargs={'TARGET_BITS': 64}),
    stock_config(
        'android-pie-arm64-rel', chromium_config_kwargs={'TARGET_BITS': 64}),
    stock_config(
        'android-pie-arm64-wpt-rel-non-cq',
        chromium_config_kwargs={'TARGET_BITS': 64}),
    stock_config(
        'android-10-arm64-rel',
        chromium_apply_config=['download_vr_test_apks'],
        gclient_apply_config=['android', 'enable_wpr_tests', 'enable_reclient'],
        chromium_config_kwargs={'TARGET_BITS': 64}),
    stock_config('android-11-x86-rel', android_config='x86_builder'),
    stock_cronet_config('android-cronet-arm-rel'),
    stock_cronet_config('android-cronet-arm64-dbg', config='Debug'),
    stock_cronet_config('android-cronet-arm64-rel'),
    stock_cronet_config('android-cronet-asan-arm-rel'),
    stock_cronet_config('android-cronet-x86-rel', android_config='x86_builder'),
    stock_cronet_config(
        'android-cronet-x86-rel-kitkat-tests',
        execution_mode=builder_spec.TEST,
        parent_buildername='android-cronet-x86-rel',
        android_config='x86_builder'),
])
