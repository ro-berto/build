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
      'chromium_apply_config': ['ninja_confirm_noop', 'archive_gpu_tests',
                                'chrome_with_codecs',
                                'internal_gles2_conform_tests'],
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
    },
    'GPU Win Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop', 'archive_gpu_tests',
                                'chrome_with_codecs',
                                'internal_gles2_conform_tests'],
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
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'parent_buildername': 'GPU Win Builder',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
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
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'parent_buildername': 'GPU Win Builder (dbg)',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'Win8 Release (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'parent_buildername': 'GPU Win Builder',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'Win8 Debug (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'parent_buildername': 'GPU Win Builder (dbg)',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'Win7 Release (ATI)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'parent_buildername': 'GPU Win Builder',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'Win7 Release (Intel)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'parent_buildername': 'GPU Win Builder',
      'testing': {
        'platform': 'win',
      },
      # Swarming is deliberately NOT enabled on this one-off configuration.
      # The GPU detection wasn't initially working (crbug.com/580331), and
      # multiple copies of the machines have to be deployed into swarming
      # in order to keep up with the faster cycle time of the tests.
      'enable_swarming': False,
    },
    'Win7 Release dEQP (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'parent_buildername': 'GPU Win Builder',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'GPU Win x64 Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop', 'archive_gpu_tests',
                                'chrome_with_codecs',
                                'internal_gles2_conform_tests'],
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
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'parent_buildername': 'GPU Win x64 Builder',
      'testing': {
        'platform': 'win',
      },
      'enable_swarming': True,
    },
    'GPU Linux Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop',
                                'archive_gpu_tests', 'chrome_with_codecs',
                                'internal_gles2_conform_tests'],
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
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'parent_buildername': 'GPU Linux Builder',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'Linux Release (Intel)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'parent_buildername': 'GPU Linux Builder',
      'testing': {
        'platform': 'linux',
      },
      # Swarming is deliberately NOT enabled on this one-off configuration.
      # Multiple copies of the machines have to be deployed into swarming
      # in order to keep up with the faster cycle time of the tests.
      'enable_swarming': False,
    },
    'Linux Release (Intel Graphics Stack)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'parent_buildername': 'GPU Linux Builder',
      'testing': {
        'platform': 'linux',
      },
      # Swarming is deliberately NOT enabled on this one-off configuration.
      # Multiple copies of the machines have to be deployed into swarming
      # in order to keep up with the faster cycle time of the tests.
      'enable_swarming': False,
    },
    'Linux Release (ATI)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'parent_buildername': 'GPU Linux Builder',
      'testing': {
        'platform': 'linux',
      },
      # Swarming is deliberately NOT enabled on this one-off configuration.
      # Multiple copies of the machines have to be deployed into swarming
      # in order to keep up with the faster cycle time of the tests.
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
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'parent_buildername': 'GPU Linux Builder (dbg)',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },
    'Linux Release dEQP (NVIDIA)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb', 'ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'tester',
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'parent_buildername': 'GPU Linux Builder',
      'testing': {
        'platform': 'linux',
      },
      # Swarming is deliberately NOT enabled on this one-off configuration.
      # TODO(kbr): it isn't clear whether these tests will shard properly
      # on Linux, so wait to make that change until a subsequent CL.
      'enable_swarming': False,
    },
    'GPU Mac Builder': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop', 'archive_gpu_tests',
                                'chrome_with_codecs',
                                'internal_gles2_conform_tests'],
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
    },
    'GPU Mac Builder (dbg)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop', 'archive_gpu_tests',
                                'chrome_with_codecs',
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
        'platform': 'mac',
      },
      'enable_swarming': True,
      'use_isolate': True,
    },
    'Mac 10.10 Release (Intel)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'GPU Mac Builder',
      'testing': {
        'platform': 'mac',
      },
      'enable_swarming': True,
    },
    'Mac 10.10 Debug (Intel)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'GPU Mac Builder (dbg)',
      'testing': {
        'platform': 'mac',
      },
      'enable_swarming': True,
    },
    'Mac 10.10 Release (ATI)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
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
    'Mac 10.10 Debug (ATI)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
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
    'Mac 10.10 Retina Release (AMD)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'GPU Mac Builder',
      'testing': {
        'platform': 'mac',
      },
      'enable_swarming': True,
    },
    'Mac 10.10 Retina Debug (AMD)': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['ninja_confirm_noop'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64,
      },
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'bot_type': 'tester',
      'parent_buildername': 'GPU Mac Builder (dbg)',
      'testing': {
        'platform': 'mac',
      },
      'enable_swarming': True,
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
      'test_generators': [
        steps.generate_gtest,
        steps.generate_script,
        steps.generate_isolated_script,
      ],
      'parent_buildername': 'GPU Fake Linux Builder',
      'testing': {
        'platform': 'linux',
      },
      'enable_swarming': True,
    },
  },
}
