# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps


SWARMING_DIMENSIONS = {
    'android_devices': '6',
    'cpu': None,
    'gpu': None,
    'os': 'Android',
}


SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-android-archive',
  },
  'builders': {
    'Android arm Builder (dbg)': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder',
      'compile_targets': [
        'android_builder_tests',
        'remoting_apk',
      ],
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },

    'Android arm64 Builder (dbg)': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder',
      'compile_targets': [
        'android_builder_tests'
      ],
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },

    'Android GN Builder (dbg)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
        'TARGET_ARCH': 'arm',
      },
      'android_config': 'main_builder',
       'test_generators': [
         steps.generate_gtest,
         steps.generate_script,
         steps.generate_isolated_script,
        ],
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },

    'Android Aura Builder (dbg)': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_apply_config': ['mb'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder',
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },

    'Android Aura Tester (dbg)': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android Aura Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'testing': {
        'platform': 'linux',
      },
    },

    'Jelly Bean Tester': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'testing': {
        'platform': 'linux',
      },
    },

    'KitKat Tablet Tester': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'testing': {
        'platform': 'linux',
      },
    },

    'Lollipop 64 bit Tester': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm64 Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'testing': {
        'platform': 'linux',
      },
    },

    'Lollipop Consumer Tester': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm64 Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'testing': {
        'platform': 'linux',
      },
    },

    'Lollipop Low-end Tester': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'testing': {
        'platform': 'linux',
      },
    },

    'Lollipop Phone Tester': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'testing': {
        'platform': 'linux',
      },
    },

    'Lollipop Tablet Tester': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'testing': {
        'platform': 'linux',
      },
    },

    'Marshmallow Tablet Tester': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'testing': {
        'platform': 'linux',
      },
    },

    'Android Swarm Builder': {
      'use_isolate': True,
      'enable_swarming': True,
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder',
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
      'tests': [
        steps.GTestTest('android_webview_unittests',
                        enable_swarming=True,
                        swarming_dimensions=SWARMING_DIMENSIONS),
        steps.GTestTest(
            'base_unittests',
            android_isolate_path='base/base_unittests.isolate',
            enable_swarming=True,
            swarming_dimensions=SWARMING_DIMENSIONS),
        steps.GTestTest(
            'breakpad_unittests',
            override_compile_targets=['breakpad_unittests_deps'],
            android_isolate_path='breakpad/breakpad_unittests.isolate',
            enable_swarming=True,
            swarming_dimensions=SWARMING_DIMENSIONS),
        steps.GTestTest(
            'components_unittests',
            android_isolate_path='components/components_unittests.isolate',
            enable_swarming=True,
            swarming_dimensions=SWARMING_DIMENSIONS),
        steps.GTestTest(
            'content_unittests',
            android_isolate_path='content/content_unittests.isolate',
            enable_swarming=True,
            swarming_dimensions=SWARMING_DIMENSIONS),
        steps.GTestTest('device_unittests',
                        enable_swarming=True,
                        swarming_dimensions=SWARMING_DIMENSIONS),
        steps.GTestTest('events_unittests',
                        enable_swarming=True,
                        swarming_dimensions=SWARMING_DIMENSIONS),
        steps.GTestTest('gl_tests',
                        enable_swarming=True,
                        swarming_dimensions=SWARMING_DIMENSIONS),
        steps.GTestTest('gl_unittests',
                        enable_swarming=True,
                        swarming_dimensions=SWARMING_DIMENSIONS),
        steps.GTestTest('gpu_unittests',
                        enable_swarming=True,
                        swarming_dimensions=SWARMING_DIMENSIONS),
        steps.GTestTest('ipc_tests',
                        enable_swarming=True,
                        swarming_dimensions=SWARMING_DIMENSIONS),
        steps.GTestTest(
            'media_unittests',
            android_isolate_path='media/media_unittests.isolate',
            enable_swarming=True,
            swarming_dimensions=SWARMING_DIMENSIONS),
        steps.GTestTest(
            'net_unittests',
            android_isolate_path='net/net_unittests.isolate',
            enable_swarming=True,
            swarming_dimensions=SWARMING_DIMENSIONS),
        steps.GTestTest(
            'sql_unittests',
            android_isolate_path='sql/sql_unittests.isolate',
            enable_swarming=True,
            swarming_dimensions=SWARMING_DIMENSIONS),
        steps.GTestTest('ui_android_unittests',
                        enable_swarming=True,
                        swarming_dimensions=SWARMING_DIMENSIONS),
        steps.GTestTest(
            'ui_base_unittests',
            android_isolate_path='ui/base/ui_base_tests.isolate',
            enable_swarming=True,
            swarming_dimensions=SWARMING_DIMENSIONS),
        steps.GTestTest('ui_touch_selection_unittests',
                        enable_swarming=True,
                        swarming_dimensions=SWARMING_DIMENSIONS),
        steps.GTestTest(
            'unit_tests',
            android_isolate_path='chrome/unit_tests.isolate',
            enable_swarming=True,
            swarming_dimensions=SWARMING_DIMENSIONS),
      ],
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
    },

    'Android WebView (amp)': {
      'chromium_config': 'android',
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'amp_config': 'main_pool',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'parent_buildername': 'Android arm Builder (dbg)',
      'bot_type': 'tester',
      'android_config': 'main_builder',
      'enable_swarming': False,
      'tests': [
        steps.AMPInstrumentationTest(
            test_apk='AndroidWebViewTest',
            apk_under_test='AndroidWebView',
            android_isolate_path=
                'android_webview/android_webview_test_apk.isolate',
            compile_target='android_webview_test_apk',
            device_name=['Nexus 7'], device_os=['4.4.2'],
            fallback_to_local=False,
            test_timeout=3600),
        steps.AMPInstrumentationTest(
            test_apk='AndroidWebViewTest',
            apk_under_test='AndroidWebView',
            android_isolate_path=
                'android_webview/android_webview_test_apk.isolate',
            compile_target='android_webview_test_apk',
            device_name=['Galaxy S4'], device_os=['4.4.2'],
            fallback_to_local=False,
            test_timeout=3600),
        steps.AMPInstrumentationTest(
            test_apk='AndroidWebViewTest',
            apk_under_test='AndroidWebView',
            android_isolate_path=
                'android_webview/android_webview_test_apk.isolate',
            compile_target='android_webview_test_apk',
            device_name=['Galaxy Note 3'], device_os=['4.4.2'],
            fallback_to_local=False,
            test_timeout=3600),
        steps.AMPInstrumentationTest(
            test_apk='AndroidWebViewTest',
            apk_under_test='AndroidWebView',
            android_isolate_path=
                'android_webview/android_webview_test_apk.isolate',
            compile_target='android_webview_test_apk',
            device_name=['Moto G'], device_os=['4.4.2'],
            fallback_to_local=False,
            test_timeout=3600),
        steps.AMPInstrumentationTest(
            test_apk='AndroidWebViewTest',
            apk_under_test='AndroidWebView',
            android_isolate_path=
                'android_webview/android_webview_test_apk.isolate',
            compile_target='android_webview_test_apk',
            device_name=['One M8'], device_os=['4.4.2'],
            fallback_to_local=False,
            test_timeout=3600),
      ],
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'testing': {
        'platform': 'linux',
      },
    },
  },
}
