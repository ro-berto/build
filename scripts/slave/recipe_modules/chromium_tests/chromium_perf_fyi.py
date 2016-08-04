# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps


RESULTS_URL = 'https://chromeperf.appspot.com'


def _AddBotSpec(name, platform, parent_builder, perf_id, target_bits,
                parent_master=None):
  SPEC['builders'][name] = {
    'disable_tests': True,
    'bot_type': 'tester',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': target_bits,
    },
    'parent_buildername': parent_builder,
    'chromium_config': 'chromium_perf',
    'gclient_config': 'chromium_perf',
    'testing': {
      'platform': platform,
    },
    'perf-id': perf_id,
    'results-url': RESULTS_URL,
    'tests': [
      steps.DynamicPerfTests(perf_id, platform, target_bits,
                             shard_index=0, num_host_shards=1),
    ],
  }
  if parent_master:
    SPEC['builders'][name]['parent_mastername'] = parent_master


SPEC = {
  'settings': {
    'build_gs_bucket': 'chrome-perf',
  },
  'builders': {
    'Win Clang Builder': {
      'disable_tests': True,
      'chromium_config': 'chromium_win_clang_official',
      'gclient_config': 'chromium_perf',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
      'bot_type': 'builder',
      'compile_targets': [
        'chromium_builder_perf',
      ],
      'testing': {
        'platform': 'win',
      },
      'tests': {
        steps.SizesStep(RESULTS_URL, 'win-clang-builder')
      },
    },
  },
}

_AddBotSpec(
    name='Win 7 Intel GPU Perf (Xeon)',
    platform='win',
    parent_builder='Win x64 Builder',
    perf_id='chromium-rel-win7-gpu-intel',
    target_bits=64,
    parent_master='chromium.perf')

_AddBotSpec(
    name='Win Power High-DPI Perf',
    platform='win',
    parent_builder='Win x64 Builder',
    perf_id='win-power-high-dpi',
    target_bits=64,
    parent_master='chromium.perf')

_AddBotSpec(
    name='Win Clang Perf',
    platform='win',
    parent_builder='Win Clang Builder',
    perf_id='chromium-win-clang',
    target_bits=32)

_AddBotSpec(
    name='Mac Power Dual-GPU Perf',
    platform='mac',
    parent_builder='Mac Builder',
    perf_id='mac-power-dual-gpu',
    target_bits=64,
    parent_master='chromium.perf')

_AddBotSpec(
    name='Mac Power Low-End Perf',
    platform='mac',
    parent_builder='Mac Builder',
    perf_id='mac-power-low-end',
    target_bits=64,
    parent_master='chromium.perf')

_AddBotSpec(
    name='Mac Test Retina Perf',
    platform='mac',
    parent_builder='Mac Builder',
    perf_id='mac-test-retina',
    target_bits=64,
    parent_master='chromium.perf')
