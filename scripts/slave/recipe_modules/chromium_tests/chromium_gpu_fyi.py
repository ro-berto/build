# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-gpu-fyi-archive',
    # WARNING: src-side runtest.py is only tested with chromium CQ builders.
    # Usage not covered by chromium CQ is not supported and can break
    # without notice.
    'src_side_runtest_py': True,
  },
  'builders': {
    'GPU Win Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'archive_gpu_tests',
        'build_angle_deqp_tests',
        'chrome_with_codecs',
        'internal_gles2_conform_tests',
        'mb',
        'ninja_confirm_noop',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
      'use_isolate': True,
      'checkout_dir': 'win',
    },
    'GPU Win Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'archive_gpu_tests',
        'chrome_with_codecs',
        'internal_gles2_conform_tests',
        'mb',
        'ninja_confirm_noop',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
      'use_isolate': True,
      'checkout_dir': 'win',
    },
    'Win7 Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Win Builder',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
      'serialize_tests': True,
    },
    'Win7 Debug (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Win Builder (dbg)',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
      'serialize_tests': True,
    },
    'Win10 Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Win Builder',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
      'serialize_tests': True,
    },
    'Win10 Debug (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Win Builder (dbg)',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
      'serialize_tests': True,
    },
    'Win7 Release (AMD)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Win Builder',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
      'serialize_tests': True,
    },
    'Win7 Debug (AMD)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Win Builder (dbg)',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
      'serialize_tests': True,
    },
    'Win7 Release (NVIDIA GeForce 730)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Win Builder',
      'testing': {
        'platform': 'win',
      },
      # Swarming is deliberately NOT enabled on this one-off configuration.
      # These new graphics cards are being tested at the moment.
      'enable_swarming': False,
    },
    'Win10 Release (New Intel)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Win Builder',
      'testing': {
        'platform': 'win',
      },
      # Swarming is deliberately NOT enabled on this one-off configuration.
      # This new hardware is being tested for reliability.
      'enable_swarming': False,
    },
    'Win10 Debug (New Intel)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Win Builder (dbg)',
      'testing': {
        'platform': 'win',
      },
      # Swarming is deliberately NOT enabled on this one-off configuration.
      # This new hardware is being tested for reliability.
      'enable_swarming': False,
    },
    'Win7 Release (AMD R5 230)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Win Builder',
      'testing': {
        'platform': 'win',
      },
      # Swarming is deliberately NOT enabled on this one-off configuration.
      # These new graphics cards are being tested at the moment.
      'enable_swarming': False,
    },
    'GPU Win x64 Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'archive_gpu_tests',
        'build_angle_deqp_tests',
        'chrome_with_codecs',
        'internal_gles2_conform_tests',
        'mb',
        'ninja_confirm_noop',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
      'use_isolate': True,
      'checkout_dir': 'win',
    },
    'GPU Win x64 Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'archive_gpu_tests',
        'chrome_with_codecs',
        'internal_gles2_conform_tests',
        'mb',
        'ninja_confirm_noop',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
      'use_isolate': True,
      'checkout_dir': 'win',
    },
    'Win7 x64 Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Win x64 Builder',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
      'serialize_tests': True,
    },
    'Win7 x64 Debug (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Win x64 Builder (dbg)',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
      'serialize_tests': True,
    },
    'GPU Win Clang Builder (dbg)': {
      # This bot is on the chromium.gpu.fyi waterfall to help ensure
      # that ANGLE rolls aren't reverted due to Clang build failures
      # on Windows. We don't run the binaries that are built on this
      # bot, at least not yet.
      'chromium_config': 'chromium_win_clang',
      'chromium_apply_config': ['archive_gpu_tests',
                                'chrome_with_codecs',
                                'internal_gles2_conform_tests',
                                'mb',
                                'ninja_confirm_noop',],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_PLATFORM': 'win',
        'TARGET_BITS': 64,
      },
      'compile_targets': [
        'all',
      ],
      # Recipes builds Debug builds with component=shared_library by default.
      'bot_type': 'builder',
      'testing': {
        'platform': 'win',
      },
      'use_isolate': True,
      'enable_swarming': True,
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'GPU Linux Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop',
                                'archive_gpu_tests', 'chrome_with_codecs',
                                'internal_gles2_conform_tests',
                                'build_angle_deqp_tests'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'linux',
      },
      'use_isolate': True,
      'enable_swarming': True,
      'checkout_dir': 'linux',
    },
    'GPU Linux Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop',
                                'archive_gpu_tests', 'chrome_with_codecs',
                                'internal_gles2_conform_tests'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'linux',
      },
      'use_isolate': True,
      'enable_swarming': True,
      'checkout_dir': 'linux',
    },
    'Linux Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Linux Builder',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
      'serialize_tests': True,
    },
    'Linux Release (AMD R5 230)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Linux Builder',
      'testing': {
        'platform': 'linux',
      },
      # Swarming is deliberately NOT enabled on this one-off configuration.
      # Multiple copies of the machines have to be deployed into swarming
      # in order to keep up with the faster cycle time of the tests.
      'enable_swarming': False,
    },
    'Linux Release (NVIDIA GeForce 730)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Linux Builder',
      'testing': {
        'platform': 'linux',
      },
      # Swarming is deliberately NOT enabled on this one-off configuration.
      # These new graphics cards are being tested at the moment.
      'enable_swarming': False,
    },
    'Linux Debug (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Linux Builder (dbg)',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
      'serialize_tests': True,
    },
    'Linux Release (New Intel)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Linux Builder',
      'testing': {
        'platform': 'linux',
      },
      # Swarming is deliberately NOT enabled on this one-off configuration.
      # Multiple copies of the machines have to be deployed into swarming
      # in order to keep up with the faster cycle time of the tests.
      'enable_swarming': False,
    },
    'Linux Debug (New Intel)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Linux Builder (dbg)',
      'testing': {
        'platform': 'linux',
      },
      # Swarming is deliberately NOT enabled on this one-off configuration.
      # Multiple copies of the machines have to be deployed into swarming
      # in order to keep up with the faster cycle time of the tests.
      'enable_swarming': False,
    },
    'Linux Release (AMD R7 240)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Linux Builder',
      'testing': {
        'platform': 'linux',
      },
      # Swarming is deliberately NOT enabled on this one-off configuration.
      # Multiple copies of the machines have to be deployed into swarming
      # in order to keep up with the faster cycle time of the tests.
      'enable_swarming': False,
    },
    'GPU Mac Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config':['archive_gpu_tests',
                               'chrome_with_codecs',
                               'internal_gles2_conform_tests',
                               'mb',
                               'ninja_confirm_noop',],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'mac',
      },
      'enable_swarming': True,
      'use_isolate': True,
      'checkout_dir': 'mac',
    },
    'GPU Mac Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['archive_gpu_tests',
                                'chrome_with_codecs',
                                'internal_gles2_conform_tests',
                                'mb',
                                'ninja_confirm_noop',],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'mac',
      },
      'enable_swarming': True,
      'use_isolate': True,
      'checkout_dir': 'mac',
    },
    'Mac 10.10 Release (Intel)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Mac Builder',
      'testing': {
        'platform': 'mac',
      },
      'enable_swarming': True,
      'serialize_tests': True,
    },
    'Mac 10.10 Debug (Intel)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Mac Builder (dbg)',
      'testing': {
        'platform': 'mac',
      },
      'enable_swarming': True,
      'serialize_tests': True,
    },
    'Mac 10.10 Release (AMD)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Mac Builder',
      'testing': {
        'platform': 'mac',
      },
      # Swarming is deliberately NOT enabled on this one-off configuration.
      # Multiple copies of the machines have to be deployed into swarming
      # in order to keep up with the faster cycle time of the tests.
      'enable_swarming': False,
    },
    'Mac 10.10 Debug (AMD)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Mac Builder (dbg)',
      'testing': {
        'platform': 'mac',
      },
      # Swarming is deliberately NOT enabled on this one-off configuration.
      # Multiple copies of the machines have to be deployed into swarming
      # in order to keep up with the faster cycle time of the tests.
      'enable_swarming': False,
    },
    'Mac Retina Release': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Mac Builder',
      'testing': {
        'platform': 'mac',
      },
      'enable_swarming': True,
      'serialize_tests': True,
    },
    'Mac Retina Debug': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Mac Builder (dbg)',
      'testing': {
        'platform': 'mac',
      },
      'enable_swarming': True,
      'serialize_tests': True,
    },
    'Mac 10.10 Retina Release (AMD)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Mac Builder',
      'testing': {
        'platform': 'mac',
      },
      'enable_swarming': True,
      'serialize_tests': True,
    },
    'Mac 10.10 Retina Debug (AMD)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Mac Builder (dbg)',
      'testing': {
        'platform': 'mac',
      },
      'enable_swarming': True,
      'serialize_tests': True,
    },
    'Mac 10.11 Retina Release (AMD)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Mac Builder',
      'testing': {
        'platform': 'mac',
      },
      # Swarming is deliberately NOT enabled on this one-off configuration.
      # Multiple copies of the machines have to be deployed into swarming
      # in order to keep up with the faster cycle time of the tests.
      'enable_swarming': False,
    },
    'Mac GPU ASAN Release': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'mac',
      },
      'enable_swarming': True,
      'serialize_tests': True,
    },
    'Android Release (Nexus 5)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['chrome_with_codecs', 'mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder',
      'android_apply_config': ['restart_usb', 'use_devil_adb'],
      'bot_type': 'builder_tester',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'linux',
      },
      'use_isolate': False,
      'enable_swarming': False,
    },
    'Android Release (Nexus 5X)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['chrome_with_codecs'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'arm64_builder_rel_mb',
      'android_apply_config': ['restart_usb', 'use_devil_adb'],
      'bot_type': 'builder_tester',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'linux',
      },
      'use_isolate': True,
      'enable_swarming': True,
      'checkout_dir': 'android',
    },
    'Android Release (Nexus 6)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['chrome_with_codecs', 'mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder',
      'android_apply_config': ['restart_usb', 'use_devil_adb'],
      'bot_type': 'builder_tester',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'linux',
      },
      'use_isolate': False,
      'enable_swarming': False,
    },
    'Android Release (Nexus 6P)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['chrome_with_codecs'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'arm64_builder_rel_mb',
      'android_apply_config': ['restart_usb', 'use_devil_adb'],
      'bot_type': 'builder_tester',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'linux',
      },
      'use_isolate': False,
      'enable_swarming': False,
    },
    'Android Release (Nexus 9)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['chrome_with_codecs'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'arm64_builder_rel_mb',
      'android_apply_config': ['restart_usb', 'use_devil_adb'],
      'bot_type': 'builder_tester',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'linux',
      },
      'use_isolate': False,
      'enable_swarming': False,
    },
    'Android Release (Pixel C)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['chrome_with_codecs'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'arm64_builder_rel_mb',
      'android_apply_config': ['restart_usb', 'use_devil_adb'],
      'bot_type': 'builder_tester',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'linux',
      },
      'use_isolate': False,
      'enable_swarming': False,
    },

    'GPU Fake Linux Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop',
                                'archive_gpu_tests', 'chrome_with_codecs' ],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'linux',
      },
      'use_isolate': True,
      'enable_swarming': True,
    },
    'Fake Linux Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Fake Linux Builder',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },

    # The following machines don't actually exist. They are specified
    # here only in order to allow the associated src-side JSON entries
    # to be read, and the "optional" GPU tryservers to be specified in
    # terms of them.
    'Optional Win7 Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Win Builder',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'Optional Win7 Release (AMD)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Win Builder',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'Optional Linux Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Linux Builder',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'Optional Mac 10.10 Release (Intel)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Mac Builder',
      'testing': {
        'platform': 'mac',
      },
      'enable_swarming': True,
    },
    'Optional Mac Retina Release': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Mac Builder',
      'testing': {
        'platform': 'mac',
      },
      'enable_swarming': True,
    },
    'Optional Mac 10.10 Retina Release (AMD)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Mac Builder',
      'testing': {
        'platform': 'mac',
      },
      'enable_swarming': True,
    },
    'Linux ChromiumOS Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'archive_gpu_tests',
        'chromeos',
        'internal_gles2_conform_tests',
        'mb',
        'ninja_confirm_noop',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'aura_builder',
      ],
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': False,
      'use_isolate': True,
    },
  },
}
