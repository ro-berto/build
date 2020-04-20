# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_spec

RESULTS_URL = 'https://chromeperf.appspot.com'


def _chromium_android_spec(**kwargs):
  return bot_spec.BotSpec.create(
      build_gs_bucket='chromium-android-archive', **kwargs)


SPEC = {
    'Android arm Builder (dbg)':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder_mb',
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'Android arm64 Builder (dbg)':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder_mb',
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'Android ASAN (dbg)':
        _chromium_android_spec(
            chromium_config='android_clang',
            chromium_apply_config=[
                'errorprone',
            ],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='clang_builder_mb',
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'Android x64 Builder (dbg)':
        _chromium_android_spec(
            chromium_config='android',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='x64_builder_mb',
            bot_type=bot_spec.BUILDER,
            simulation_platform='linux',
        ),
    'Android x86 Builder (dbg)':
        _chromium_android_spec(
            chromium_config='android',
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='x86_builder_mb',
            bot_type=bot_spec.BUILDER,
            simulation_platform='linux',
        ),
    'Cast Android (dbg)':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'mb',
                'mb_luci_auth',
            ],
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
    'KitKat Phone Tester (dbg)':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder_mb',
            bot_type=bot_spec.TESTER,
            parent_buildername='Android arm Builder (dbg)',
            simulation_platform='linux',
        ),
    'KitKat Phone Tester (rel)':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks', 'mb', 'mb_luci_auth'
            ],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder',
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'KitKat Tablet Tester':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm Builder (dbg)',
            bot_type=bot_spec.TESTER,
            android_config='main_builder_mb',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Marshmallow 64 bit Tester':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm64 Builder (dbg)',
            bot_type=bot_spec.TESTER,
            android_config='main_builder_mb',
            simulation_platform='linux',
        ),
    'Lollipop Phone Tester':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm Builder (dbg)',
            bot_type=bot_spec.TESTER,
            android_config='main_builder_mb',
            simulation_platform='linux',
        ),
    'Lollipop Tablet Tester':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm Builder (dbg)',
            bot_type=bot_spec.TESTER,
            android_config='main_builder_mb',
            simulation_platform='linux',
            serialize_tests=True,
        ),
    'Marshmallow Phone Tester (rel)':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',

                # This is specified because 'android_n5x_swarming_rel'
                # builder is one of the slowest builder in CQ
                # (crbug.com/804251).
                'goma_high_parallel',
            ],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            android_config='main_builder_mb',
            bot_type=bot_spec.BUILDER_TESTER,
            simulation_platform='linux',
        ),
    'Marshmallow Tablet Tester':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm Builder (dbg)',
            bot_type=bot_spec.TESTER,
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
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm64 Builder (dbg)',
            bot_type=bot_spec.TESTER,
            android_config='main_builder_mb',
            simulation_platform='linux',
        ),
    'Oreo Phone Tester':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm64 Builder (dbg)',
            bot_type=bot_spec.TESTER,
            android_config='main_builder_mb',
            simulation_platform='linux',
        ),
    'android-pie-arm64-dbg':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm64 Builder (dbg)',
            bot_type=bot_spec.TESTER,
            android_config='main_builder_mb',
            simulation_platform='linux',
        ),
    'Android WebView L (dbg)':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm Builder (dbg)',
            bot_type=bot_spec.TESTER,
            android_config='main_builder_mb',
            simulation_platform='linux',
        ),
    'Android WebView M (dbg)':
        _chromium_android_spec(
            chromium_config='android',
            chromium_apply_config=[
                'download_vr_test_apks',
            ],
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm64 Builder (dbg)',
            bot_type=bot_spec.TESTER,
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
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm64 Builder (dbg)',
            bot_type=bot_spec.TESTER,
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
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm64 Builder (dbg)',
            bot_type=bot_spec.TESTER,
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
            gclient_config='chromium',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android',
            },
            parent_buildername='Android arm64 Builder (dbg)',
            bot_type=bot_spec.TESTER,
            android_config='main_builder_mb',
            android_apply_config=['remove_all_system_webviews'],
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
      'chromium_apply_config': ['mb', 'mb_luci_auth'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
          'BUILD_CONFIG': config,
          'TARGET_BITS': 32,
          'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder',
      'bot_type': bot_spec.BUILDER_TESTER,
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
      chromium_tests_apply_config=['staging'],
      **kwargs)


SPEC.update([
    stock_config(
        'android-arm64-proguard-rel',
        chromium_apply_config=['download_vr_test_apks'],
        chromium_config_kwargs={'TARGET_BITS': 64}),
    stock_config('android-incremental-dbg', config='Debug'),
    stock_config(
        'android-kitkat-arm-rel',
        chromium_apply_config=['download_vr_test_apks'],
        chromium_config_kwargs={'TARGET_BITS': 32}),
    stock_config(
        'android-lollipop-arm-rel',
        chromium_apply_config=['download_vr_test_apks'],
        chromium_config_kwargs={'TARGET_BITS': 32}),
    stock_config(
        'android-marshmallow-arm64-rel',
        chromium_apply_config=[
            'download_vr_test_apks',
            # This is specified because 'android-marshmallow-arm64-rel' builder
            # is one of the slowest builder in CQ (crbug.com/804251).
            'goma_high_parallel'
        ],
        chromium_config_kwargs={'TARGET_BITS': 64}),
    stock_config(
        'android-pie-arm64-rel', chromium_config_kwargs={'TARGET_BITS': 64}),
    stock_config('android-pie-x86-rel', android_config='x86_builder'),
    stock_config(
        'android-10-arm64-rel',
        chromium_apply_config=['download_vr_test_apks'],
        chromium_config_kwargs={'TARGET_BITS': 64}),
    stock_cronet_config('android-cronet-arm-dbg', config='Debug'),
    stock_cronet_config('android-cronet-arm-rel'),
    stock_cronet_config('android-cronet-arm64-dbg', config='Debug'),
    stock_cronet_config('android-cronet-arm64-rel'),
    stock_cronet_config('android-cronet-asan-arm-rel'),
    stock_cronet_config(
        'android-cronet-kitkat-arm-rel',
        bot_type=bot_spec.TESTER,
        parent_buildername='android-cronet-arm-rel'),
    stock_cronet_config(
        'android-cronet-lollipop-arm-rel',
        bot_type=bot_spec.TESTER,
        parent_buildername='android-cronet-arm-rel'),
    stock_cronet_config(
        'android-cronet-marshmallow-arm64-rel',
        bot_type=bot_spec.TESTER,
        parent_buildername='android-cronet-arm64-rel'),
    stock_cronet_config('android-cronet-x86-dbg', config='Debug'),
    stock_cronet_config('android-cronet-x86-rel'),
])
