# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps


def _GetTargetName(platform, target_bits):
  return ('Release_x64' if platform is 'win' and target_bits is 64
            else 'Release')

def _Spec(platform, parent_builder, perf_id, index, num_shards, target_bits):
  return {
    'disable_tests': True,
    'bot_type': 'tester',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': target_bits,
    },
    'parent_buildername': parent_builder,
    'recipe_config': 'perf',
    'testing': {
      'platform': platform,
    },
    'tests': [
      steps.DynamicPerfTests(
          _GetTargetName(platform, target_bits).lower(),
          perf_id, index, num_shards),
    ],
  }


def _AddBotSpec(name, platform, parent_builder, perf_id, target_bits,
  num_shards):
  if num_shards > 1:
    for i in range(0, num_shards):
      builder_name = "%s (%d)" % (name, i + 1)
      SPEC['builders'][builder_name] = _Spec(platform, parent_builder, perf_id,
        i, num_shards, target_bits)
  else:
    SPEC['builders'][name] = _Spec(platform, parent_builder, perf_id,
        0, 1, target_bits)


SPEC = {
  'settings': {
    'build_gs_bucket': 'chrome-perf',
  },
  'builders': {
    'android_nexus5_oilpan_perf': {
      'disable_tests': True,
      'bot_type': 'tester',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android',
      },
      'gclient_config': 'perf',
      'gclient_apply_config': ['android'],
      'parent_buildername': 'android_oilpan_builder',
      'recipe_config': 'perf',
      'android_config': 'perf',
      'testing': {
        'platform': 'linux',
      },
      'tests': [
        steps.AndroidPerfTests('android-nexus5-oilpan', 1),
      ],
    },
    'android_oilpan_builder': {
      'disable_tests': True,
      'recipe_config': 'chromium_oilpan',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
        'TARGET_ARCH': 'arm',
      },
      'bot_type': 'builder',
      'testing': {
        'platform': 'linux',
      },
      'chromium_apply_config': ['chromium_perf', 'android'],
      'gclient_apply_config': ['android', 'perf'],
    },
    'Linux Oilpan Builder': {
      'disable_tests': True,
      'recipe_config': 'chromium_oilpan',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'chromium_builder_perf',
      ],
      'testing': {
        'platform': 'linux',
      },
      'chromium_apply_config': ['chromium_perf']
    },
    'Win x64 FYI Builder': {
      'disable_tests': True,
      'recipe_config': 'official',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'chromium_builder_perf',
      ],
      'testing': {
        'platform': 'win',
      },
      'chromium_apply_config': ['chromium_perf_fyi']
    },
  },
}

_AddBotSpec(
    name='Linux Oilpan Perf',
    platform='linux',
    parent_builder='Linux Oilpan Builder',
    perf_id='linux-oilpan-release',
    target_bits=64,
    num_shards=4)

_AddBotSpec(
    name='Win 7 ATI GPU Perf',
    platform='win',
    parent_builder='Win x64 FYI Builder',
    perf_id='chromium-rel-win7-gpu-ati',
    target_bits=64,
    num_shards=1)
# TODO(eakuefner): Rotate roles for evaluation.
# _AddBotSpec(
#     name='Win 7 Intel GPU Perf',
#     platform='win',
#     parent_builder='Win x64 FYI Builder',
#     perf_id='chromium-rel-win7-gpu-intel',
#     target_bits=64,
#     num_shards=1)
_AddBotSpec(
    name='Win 7 Nvidia GPU Perf',
    platform='win',
    parent_builder='Win x64 FYI Builder',
    perf_id='chromium-rel-win7-gpu-nvidia',
    target_bits=64,
    num_shards=1)
