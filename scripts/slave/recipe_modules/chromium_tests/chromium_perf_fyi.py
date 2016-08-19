# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import chromium_perf

import DEPS
CHROMIUM_CONFIG_CTX = DEPS['chromium'].CONFIG_CTX
GCLIENT_CONFIG_CTX = DEPS['gclient'].CONFIG_CTX


SPEC = {
  'builders': {},
  'settings': chromium_perf.SPEC['settings'],
}


@CHROMIUM_CONFIG_CTX(includes=['chromium_win_clang_official'])
def chromium_perf_clang(c):
  pass


@GCLIENT_CONFIG_CTX(includes=['chromium_perf'])
def chromium_perf_clang(c):
  pass


def _AddBuildSpec(name, perf_id, platform, config_name='chromium_perf',
                  target_bits=64):
  SPEC['builders'][name] = chromium_perf.BuildSpec(
      config_name, perf_id, platform, target_bits)


def _AddTestSpec(name, perf_id, platform,
                 parent_builder=None, target_bits=64):
  parent_buildername = (parent_builder or
      chromium_perf.builders[platform][target_bits])
  spec = chromium_perf.TestSpec('chromium_perf', parent_buildername, perf_id,
                                platform, target_bits, 0, 1, 1)
  if not parent_builder:
    spec['parent_mastername'] = 'chromium.perf'
  spec['disable_tests'] = True
  SPEC['builders'][name] = spec


_AddTestSpec('Win 7 Intel GPU Perf (Xeon)', 'chromium-rel-win7-gpu-intel',
             'win')
_AddTestSpec('Win Power High-DPI Perf', 'win-power-high-dpi', 'win')


_AddTestSpec('Mac Power Dual-GPU Perf', 'mac-power-dual-gpu', 'mac')
_AddTestSpec('Mac Power Low-End Perf', 'mac-power-low-end', 'mac')
_AddTestSpec('Mac Test Retina Perf', 'mac-test-retina', 'mac')


_AddBuildSpec('Win Clang Builder', 'win-clang-builder', 'win',
              config_name='chromium_perf_clang', target_bits=32)
_AddTestSpec('Win Clang Perf', 'chromium-win-clang', 'win',
             parent_builder='Win Clang Builder', target_bits=32)
