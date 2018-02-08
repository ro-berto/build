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
      'checkout_dir': 'win',
    },
    'GPU Win Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
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
      'checkout_dir': 'win',
    },
    'GPU Win dEQP Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'build_angle_deqp_tests',
        'chrome_with_codecs',
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
      # When trybots are set up which mirror this configuration,
      # compiling might induce a clobber build if the pinned
      # buildtools version is different from Chromium's default. This
      # is a risk we're willing to take because checkouts take a lot
      # of disk space, and this is expected to be a corner case rather
      # than the common case.
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
      'serialize_tests': True,
    },
    'Win10 dEQP Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Win dEQP Builder',
      'testing': {
        'platform': 'win',
      },
      'serialize_tests': True,
    },
    'Win10 Experimental Release (NVIDIA)': {
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
      'serialize_tests': True,
    },
    'Win7 dEQP Release (AMD)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Win dEQP Builder',
      'testing': {
        'platform': 'win',
      },
      'serialize_tests': True,
    },
    'Win10 Release (Intel HD 630)': {
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
      'serialize_tests': True,
    },
    'GPU Win x64 Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
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
      'checkout_dir': 'win',
    },
    'GPU Win x64 Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
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
      'checkout_dir': 'win',
    },
    'GPU Win x64 dEQP Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
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
      # When trybots are set up which mirror this configuration,
      # compiling might induce a clobber build if the pinned
      # buildtools version is different from Chromium's default. This
      # is a risk we're willing to take because checkouts take a lot
      # of disk space, and this is expected to be a corner case rather
      # than the common case.
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
      'serialize_tests': True,
    },
    'Win7 x64 dEQP Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Win x64 dEQP Builder',
      'testing': {
        'platform': 'win',
      },
      'serialize_tests': True,
    },
    'GPU Win Clang Builder (dbg)': {
      # This bot is on the chromium.gpu.fyi waterfall to help ensure
      # that ANGLE rolls aren't reverted due to Clang build failures
      # on Windows. We don't run the binaries that are built on this
      # bot, at least not yet.
      'chromium_config': 'chromium_win_clang',
      'chromium_apply_config': ['chrome_with_codecs',
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
      # Workaround so that recipes doesn't add random build targets to our
      # compile line. We want to build everything.
      'add_tests_as_compile_targets': False,
    },
    'GPU Linux Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop',
                                'chrome_with_codecs',
                                'internal_gles2_conform_tests',
                                'build_angle_deqp_tests',
                                'fetch_telemetry_dependencies'],
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
      'checkout_dir': 'linux',
    },
    'GPU Linux Ozone Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': [
        'internal_gles2_conform_tests',
        'mb',
        'ninja_confirm_noop',
        'ozone',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
    },
    'GPU Linux Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop',
                                'chrome_with_codecs',
                                'internal_gles2_conform_tests',
                                'fetch_telemetry_dependencies'],
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
      'checkout_dir': 'linux',
    },
    'GPU Linux dEQP Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop',
                                'chrome_with_codecs',
                                'internal_gles2_conform_tests',
                                'build_angle_deqp_tests',
                                'fetch_telemetry_dependencies'],
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
      # When trybots are set up which mirror this configuration,
      # compiling might induce a clobber build if the pinned
      # buildtools version is different from Chromium's default. This
      # is a risk we're willing to take because checkouts take a lot
      # of disk space, and this is expected to be a corner case rather
      # than the common case.
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
      'serialize_tests': True,
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
      'serialize_tests': True,
    },
    'Linux dEQP Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Linux dEQP Builder',
      'testing': {
        'platform': 'linux',
      },
      'serialize_tests': True,
    },
    'Linux Release (Intel HD 630)': {
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
      'serialize_tests': True,
    },
    'Linux GPU TSAN Release': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb',
                                'ninja_confirm_noop',
                                'fetch_telemetry_dependencies'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal',
                               'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'linux',
      },
      'serialize_tests': True,
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
    },
    'GPU Mac Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config':['chrome_with_codecs',
                               'internal_gles2_conform_tests',
                               'mb',
                               'ninja_confirm_noop',
                               'fetch_telemetry_dependencies'],
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
      'checkout_dir': 'mac',
    },
    'GPU Mac Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['chrome_with_codecs',
                                'internal_gles2_conform_tests',
                                'mb',
                                'ninja_confirm_noop',
                                'fetch_telemetry_dependencies'],
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
      'checkout_dir': 'mac',
    },
    'GPU Mac dEQP Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config':['chrome_with_codecs',
                               'internal_gles2_conform_tests',
                               'mb',
                               'ninja_confirm_noop',
                               'fetch_telemetry_dependencies'],
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
      # When trybots are set up which mirror this configuration,
      # compiling might induce a clobber build if the pinned
      # buildtools version is different from Chromium's default. This
      # is a risk we're willing to take because checkouts take a lot
      # of disk space, and this is expected to be a corner case rather
      # than the common case.
      'checkout_dir': 'mac',
    },
    'Mac Release (Intel)': {
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
      'serialize_tests': True,
    },
    'Mac Debug (Intel)': {
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
      'serialize_tests': True,
    },
    'Mac Pro Release (AMD)': {
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
    },
    'Mac Pro Debug (AMD)': {
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
    },
    'Mac Retina Release (NVIDIA)': {
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
      'serialize_tests': True,
    },
    'Mac Retina Debug (NVIDIA)': {
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
      'serialize_tests': True,
    },
    'Mac Retina Release (AMD)': {
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
      'serialize_tests': True,
    },
    'Mac Retina Debug (AMD)': {
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
      'serialize_tests': True,
    },
    'Mac Experimental Release (Intel)': {
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
      'serialize_tests': True,
    },
    'Mac Experimental Retina Release (AMD)': {
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
      'serialize_tests': True,
    },
    'Mac Experimental Retina Release (NVIDIA)': {
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
    },
    'Mac GPU ASAN Release': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb',
                                'ninja_confirm_noop',
                                'fetch_telemetry_dependencies'],
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
      'serialize_tests': True,
    },
    'Mac dEQP Release AMD': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb',
                                'ninja_confirm_noop',
                                'fetch_telemetry_dependencies'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Mac dEQP Builder',
      'testing': {
        'platform': 'mac',
      },
      'serialize_tests': True,
    },
    'Mac dEQP Release Intel': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb',
                                'ninja_confirm_noop',
                                'fetch_telemetry_dependencies'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Mac dEQP Builder',
      'testing': {
        'platform': 'mac',
      },
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
    },
    'Android Release (Nexus 5X)': {
      'chromium_config': 'android',
      'chromium_apply_config': [
        'chrome_with_codecs',
        'download_vr_test_apks',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'arm64_builder_rel_mb',
      'bot_type': 'builder_tester',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'linux',
      },
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
      'bot_type': 'builder_tester',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'linux',
      },
      'checkout_dir': 'android',
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
    },
    'Android Release (NVIDIA Shield TV)': {
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
    },
    'Android dEQP Release (Nexus 5X)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['chrome_with_codecs'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'arm64_builder_rel_mb',
      'bot_type': 'builder_tester',
      'compile_targets': [
      ],
      'testing': {
        'platform': 'linux',
      },
      'checkout_dir': 'android',
    },

    'GPU Fake Linux Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop',
                                'chrome_with_codecs' ],
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
    },

    'Linux Ozone (Intel)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU Linux Ozone Builder',
      'testing': {
        'platform': 'linux',
      },
    },

    # The following machines don't actually exist. They are specified
    # here only in order to allow the associated src-side JSON entries
    # to be read, and the "optional" GPU tryservers to be specified in
    # terms of them.
    'Optional Win10 Release (NVIDIA)': {
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
    },
    'Optional Win10 Release (Intel HD 630)': {
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
    },
    'Optional Linux Release (Intel HD 630)': {
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
    },
    'Optional Mac Release (Intel)': {
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
    },
    'Optional Mac Retina Release (NVIDIA)': {
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
    },
    'Optional Mac Retina Release (AMD)': {
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
    },

    # This machine doesn't really exist either; it is a separate
    # configuration because we don't have the capacity to run all of
    # the Win AMD bot's tests on the win_angle_rel_ng tryserver.
    'Win7 ANGLE Tryserver (AMD)': {
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
      'serialize_tests': True,
    },
  },
}
