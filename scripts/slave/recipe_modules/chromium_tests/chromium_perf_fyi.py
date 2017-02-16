# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import chromium_perf
from . import steps

import DEPS
CHROMIUM_CONFIG_CTX = DEPS['chromium'].CONFIG_CTX
GCLIENT_CONFIG_CTX = DEPS['gclient'].CONFIG_CTX


SPEC = {
  'builders': {
    'Battor Agent Linux': {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64,
      },
      'bot_type': 'builder',
      'testing': { 'platform': 'linux' },
    },
  },
  'settings': chromium_perf.SPEC['settings'],
}


@CHROMIUM_CONFIG_CTX(includes=['chromium_win_clang_official', 'mb'])
def chromium_perf_clang(c):
  pass


@GCLIENT_CONFIG_CTX(includes=['chromium_perf'])
def chromium_perf_clang(c):
  pass


def _AddBuildSpec(name, perf_id, platform, config_name='chromium_perf',
                  target_bits=64, enable_swarming=False,
                  extra_compile_targets=None, force_exparchive=False):
  SPEC['builders'][name] = chromium_perf.BuildSpec(
      config_name, perf_id, platform, target_bits, enable_swarming,
      extra_compile_targets=extra_compile_targets,
      force_exparchive=force_exparchive)


def _AddTestSpec(name, perf_id, platform, num_device_shards=1,
                 parent_buildername=None, target_bits=64):
  tests = [steps.DynamicPerfTests(
      perf_id, platform, target_bits,
      num_device_shards=num_device_shards, num_host_shards=1, shard_index=0)]

  spec = chromium_perf.TestSpec(
      'chromium_perf', perf_id, platform, target_bits,
      parent_buildername=parent_buildername, tests=tests)
  if not parent_buildername:
    spec['parent_mastername'] = 'chromium.perf'
  else:
    spec['parent_mastername'] = 'chromium.perf.fyi'

  SPEC['builders'][name] = spec


def _AddIsolatedTestSpec(name, perf_id, platform,
                         parent_buildername, target_bits=64):
  spec = chromium_perf.TestSpec('chromium_perf', perf_id, platform, target_bits,
                                parent_buildername=parent_buildername)
  spec['enable_swarming'] = True
  SPEC['builders'][name] = spec


_AddBuildSpec('Android Builder FYI', 'android', 'android', target_bits=32,
              extra_compile_targets=['android_tools',
                                     'cc_perftests',
                                     'chrome_public_apk',
                                     'gpu_perftests',
                                     'push_apps_to_background_apk',
                                     'system_webview_apk',
                                     'system_webview_shell_apk',])

_AddTestSpec('Android Power Nexus 5X Perf', 'fyi-android-power-nexus-5x',
             'android', target_bits=32, num_device_shards=7,
             parent_buildername='Android Builder FYI')

_AddIsolatedTestSpec('Android Swarming N5X Tester', 'fyi-android-swarming-n5x',
                     'android', parent_buildername='Android Builder FYI')

_AddBuildSpec('Win Builder FYI', 'win', 'win', enable_swarming=True,
              force_exparchive=True)
_AddIsolatedTestSpec('Win 10 Low-End Perf Tests', 'win-10-low-end', 'win',
                     parent_buildername='Win Builder FYI')
_AddIsolatedTestSpec('Win 10 4 Core Low-End Perf Tests',
                     'win-10-4-core-low-end', 'win',
                     parent_buildername='Win Builder FYI')
_AddTestSpec('Win 7 Intel GPU Perf (Xeon)', 'chromium-rel-win7-gpu-intel',
             'win')
_AddTestSpec('Win Power High-DPI Perf', 'win-power-high-dpi', 'win')


_AddTestSpec('Mac Power Dual-GPU Perf', 'mac-power-dual-gpu', 'mac')
_AddTestSpec('Mac Power Low-End Perf', 'mac-power-low-end', 'mac')
_AddTestSpec('Mac Test Retina Perf', 'mac-test-retina', 'mac')


_AddBuildSpec('Win Clang Builder', 'win-clang-builder', 'win',
              config_name='chromium_perf_clang', target_bits=32)
_AddTestSpec('Win Clang Perf', 'chromium-win-clang', 'win',
             parent_buildername='Win Clang Builder', target_bits=32)
_AddTestSpec('Win Clang Perf Ref', 'chromium-win-clang-ref', 'win',
             parent_buildername='Win Builder FYI', target_bits=32)
