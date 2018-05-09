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
    'GPU FYI Win Builder': {
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
      'testing': {
        'platform': 'win',
      },
      'checkout_dir': 'win',
    },
    'GPU FYI Win Builder (dbg)': {
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
      'testing': {
        'platform': 'win',
      },
      'checkout_dir': 'win',
    },
    'GPU FYI Win dEQP Builder': {
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
    'Win7 FYI Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Win Builder',
      'testing': {
        'platform': 'win',
      },
      'serialize_tests': True,
    },
    'Win7 FYI Debug (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Win Builder (dbg)',
      'testing': {
        'platform': 'win',
      },
      'serialize_tests': True,
    },
    'Win10 FYI dEQP Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Win dEQP Builder',
      'testing': {
        'platform': 'win',
      },
      'serialize_tests': True,
    },
    'Win10 FYI Exp Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Win Builder',
      'testing': {
        'platform': 'win',
      },
      'serialize_tests': True,
    },
    'Win10 FYI Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Win Builder',
      'testing': {
        'platform': 'win',
      },
      'serialize_tests': True,
    },
    'Win10 FYI Debug (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Win Builder (dbg)',
      'testing': {
        'platform': 'win',
      },
      'serialize_tests': True,
    },
    'Win7 FYI Release (AMD)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Win Builder',
      'testing': {
        'platform': 'win',
      },
      'serialize_tests': True,
    },
    'Win7 FYI Debug (AMD)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Win Builder (dbg)',
      'testing': {
        'platform': 'win',
      },
      'serialize_tests': True,
    },
    'Win7 FYI dEQP Release (AMD)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Win dEQP Builder',
      'testing': {
        'platform': 'win',
      },
      'serialize_tests': True,
    },
    'Win10 FYI Release (Intel HD 630)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Win Builder',
      'testing': {
        'platform': 'win',
      },
      'serialize_tests': True,
    },
    'Win10 FYI Exp Release (Intel HD 630)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Win Builder',
      'testing': {
        'platform': 'win',
      },
      'serialize_tests': True,
    },
    'GPU FYI Win x64 Builder': {
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
      'testing': {
        'platform': 'win',
      },
      'checkout_dir': 'win',
    },
    'GPU FYI Win x64 Builder (dbg)': {
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
      'testing': {
        'platform': 'win',
      },
      'checkout_dir': 'win',
    },
    'GPU FYI Win x64 dEQP Builder': {
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
    'Win7 FYI x64 Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Win x64 Builder',
      'testing': {
        'platform': 'win',
      },
      'serialize_tests': True,
    },
    'Win7 FYI x64 Debug (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Win x64 Builder (dbg)',
      'testing': {
        'platform': 'win',
      },
      'serialize_tests': True,
    },
    'Win7 FYI x64 dEQP Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Win x64 dEQP Builder',
      'testing': {
        'platform': 'win',
      },
      'serialize_tests': True,
    },
    'GPU FYI Win Clang Builder (dbg)': {
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
    'GPU FYI Linux Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop',
                                'chrome_with_codecs',
                                'internal_gles2_conform_tests',
                                'build_angle_deqp_tests'],
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
      'checkout_dir': 'linux',
    },
    'GPU FYI Linux Ozone Builder': {
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
    'GPU FYI Linux Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop',
                                'chrome_with_codecs',
                                'internal_gles2_conform_tests'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
      'checkout_dir': 'linux',
    },
    'GPU FYI Linux dEQP Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop',
                                'chrome_with_codecs',
                                'internal_gles2_conform_tests',
                                'build_angle_deqp_tests'],
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
      # When trybots are set up which mirror this configuration,
      # compiling might induce a clobber build if the pinned
      # buildtools version is different from Chromium's default. This
      # is a risk we're willing to take because checkouts take a lot
      # of disk space, and this is expected to be a corner case rather
      # than the common case.
      'checkout_dir': 'linux',
    },
    'Linux FYI Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Linux Builder',
      'testing': {
        'platform': 'linux',
      },
      'serialize_tests': True,
    },
    'Linux FYI Debug (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Linux Builder (dbg)',
      'testing': {
        'platform': 'linux',
      },
      'serialize_tests': True,
    },
    'Linux FYI dEQP Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Linux dEQP Builder',
      'testing': {
        'platform': 'linux',
      },
      'serialize_tests': True,
    },
    'Linux FYI Release (Intel HD 630)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Linux Builder',
      'testing': {
        'platform': 'linux',
      },
      'serialize_tests': True,
    },
    'Linux FYI GPU TSAN Release': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb',
                                'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal',
                               'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
      'serialize_tests': True,
    },
    'Linux FYI Release (AMD R7 240)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Linux Builder',
      'testing': {
        'platform': 'linux',
      },
      'serialize_tests': True,
    },
    'GPU FYI Mac Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config':['chrome_with_codecs',
                               'internal_gles2_conform_tests',
                               'mb',
                               'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'mac',
      },
      'checkout_dir': 'mac',
    },
    'GPU FYI Mac Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['chrome_with_codecs',
                                'internal_gles2_conform_tests',
                                'mb',
                                'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'mac',
      },
      'checkout_dir': 'mac',
    },
    'GPU FYI Mac dEQP Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config':['chrome_with_codecs',
                               'internal_gles2_conform_tests',
                               'mb',
                               'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
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
    'Mac FYI Release (Intel)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Mac Builder',
      'testing': {
        'platform': 'mac',
      },
      'serialize_tests': True,
    },
    'Mac FYI Debug (Intel)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Mac Builder (dbg)',
      'testing': {
        'platform': 'mac',
      },
      'serialize_tests': True,
    },
    'Mac Pro FYI Release (AMD)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Mac Builder',
      'testing': {
        'platform': 'mac',
      },
      'serialize_tests': True,
    },
    'Mac FYI Retina Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Mac Builder',
      'testing': {
        'platform': 'mac',
      },
      'serialize_tests': True,
    },
    'Mac FYI Retina Debug (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Mac Builder (dbg)',
      'testing': {
        'platform': 'mac',
      },
      'serialize_tests': True,
    },
    'Mac FYI Retina Release (AMD)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Mac Builder',
      'testing': {
        'platform': 'mac',
      },
      'serialize_tests': True,
    },
    'Mac FYI Retina Debug (AMD)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Mac Builder (dbg)',
      'testing': {
        'platform': 'mac',
      },
      'serialize_tests': True,
    },
    'Mac FYI Experimental Release (Intel)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Mac Builder',
      'testing': {
        'platform': 'mac',
      },
      'serialize_tests': True,
    },
    'Mac FYI Experimental Retina Release (AMD)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Mac Builder',
      'testing': {
        'platform': 'mac',
      },
      'serialize_tests': True,
    },
    'Mac FYI Experimental Retina Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Mac Builder',
      'testing': {
        'platform': 'mac',
      },
      'serialize_tests': True,
    },
    'Mac FYI GPU ASAN Release': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb',
                                'ninja_confirm_noop'],
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
    'Mac FYI dEQP Release AMD': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb',
                                'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Mac dEQP Builder',
      'testing': {
        'platform': 'mac',
      },
      'serialize_tests': True,
    },
    'Mac FYI dEQP Release Intel': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb',
                                'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['chrome_internal', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Mac dEQP Builder',
      'testing': {
        'platform': 'mac',
      },
      'serialize_tests': True,
    },
    'Android FYI Release (Nexus 5)': {
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
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
      'checkout_dir': 'android',
    },
    'Android FYI Release (Nexus 5X)': {
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
      'testing': {
        'platform': 'linux',
      },
      'checkout_dir': 'android',
    },
    'Android FYI Release (Nexus 6)': {
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
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
      'checkout_dir': 'android',
    },
    'Android FYI Release (Nexus 6P)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['chrome_with_codecs'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'arm64_builder_rel_mb',
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
      'checkout_dir': 'android',
    },
    'Android FYI Release (Nexus 9)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['chrome_with_codecs'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'arm64_builder_rel_mb',
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
      'checkout_dir': 'android',
    },
    'Android FYI Release (NVIDIA Shield TV)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['chrome_with_codecs'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'arm64_builder_rel_mb',
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
      'checkout_dir': 'android',
    },
    'Android FYI dEQP Release (Nexus 5X)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['chrome_with_codecs'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'arm64_builder_rel_mb',
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
      'checkout_dir': 'android',
    },
    'Android FYI 32 Vk Release (Nexus 5X)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['chrome_with_codecs'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder_mb',
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
      },
      'checkout_dir': 'android',
    },
    'Android FYI 64 Vk Release (Nexus 5X)': {
      'chromium_config': 'android',
      'chromium_apply_config': ['chrome_with_codecs'],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android', 'angle_top_of_tree'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder_mb',
      'bot_type': 'builder_tester',
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

    'Linux FYI Ozone (Intel)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'parent_buildername': 'GPU FYI Linux Ozone Builder',
      'testing': {
        'platform': 'linux',
      },
      'serialize_tests': True,
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
      'parent_buildername': 'GPU FYI Win Builder',
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
      'parent_buildername': 'GPU FYI Win Builder',
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
      'parent_buildername': 'GPU FYI Linux Builder',
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
      'parent_buildername': 'GPU FYI Linux Builder',
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
      'parent_buildername': 'GPU FYI Mac Builder',
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
      'parent_buildername': 'GPU FYI Mac Builder',
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
      'parent_buildername': 'GPU FYI Mac Builder',
      'testing': {
        'platform': 'mac',
      },
    },
    'Optional Android Release (Nexus 5X)': {
      'chromium_config': 'android',
      'chromium_apply_config': [
        'chrome_with_codecs',
        'download_vr_test_apks',

        # This is specified in order to match the same configuration
        # in 'chromium.android:Marshmallow Phone Tester (rel)'.
        'goma_high_parallel',
      ],
      'gclient_config': 'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android',
      },
      'android_config': 'main_builder_mb',
      'bot_type': 'builder_tester',
      'testing': {
        'platform': 'linux',
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
      'parent_buildername': 'GPU FYI Win Builder',
      'testing': {
        'platform': 'win',
      },
      'serialize_tests': True,
    },
  },
}
