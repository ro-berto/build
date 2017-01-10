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


@CHROMIUM_CONFIG_CTX(includes=['chromium_perf', 'goma_hermetic_fallback'])
def tryserver_chromium_perf(c):
  # Bisects may build using old toolchains, so goma_hermetic_fallback is
  # required. See https://codereview.chromium.org/1015633002

  # HACK(shinyak): In perf builder, goma often fails with 'reached max
  # number of active fail fallbacks'. In fail fast mode, we cannot make the
  # number infinite currently.
  #
  # After the goma side fix, this env should be removed.
  # See http://crbug.com/606987
  c.compile_py.goma_max_active_fail_fallback_tasks = 1024


@GCLIENT_CONFIG_CTX(includes=['chromium_perf'])
def tryserver_chromium_perf(c):
  soln = c.solutions.add()
  soln.name = 'catapult'
  soln.url = ('https://chromium.googlesource.com/external/github.com/'
              'catapult-project/catapult.git')


def _AddBuildSpec(name, platform, target_bits=64):
  # We run sizes with no perf_id for perf tryjobs. http://crbug.com/610772
  SPEC['builders'][name] = chromium_perf.BuildSpec(
      'tryserver_chromium_perf', None, platform, target_bits)


def _AddTestSpec(name, platform, target_bits=64):
  SPEC['builders'][name] = chromium_perf.TestSpec(
      'tryserver_chromium_perf', None, platform, target_bits)


_AddBuildSpec('android_perf_bisect_builder', 'android', target_bits=32)
_AddBuildSpec('android_arm64_perf_bisect_builder', 'android')
_AddBuildSpec('win_perf_bisect_builder', 'win', target_bits=32)
_AddBuildSpec('winx64_bisect_builder', 'win')
_AddBuildSpec('mac_perf_bisect_builder', 'mac')
_AddBuildSpec('linux_perf_bisect_builder', 'linux')


_AddTestSpec('winx64_10_perf_cq', 'win')
_AddTestSpec('mac_retina_perf_cq', 'mac')
_AddTestSpec('linux_perf_cq', 'linux')


_AddTestSpec('win_fyi_perf_bisect', 'win', target_bits=32)
_AddTestSpec('mac_fyi_perf_bisect', 'mac')
_AddTestSpec('linux_fyi_perf_bisect', 'linux')


_AddTestSpec('winx64_zen_perf_bisect', 'win')
_AddTestSpec('winx64_high_dpi_perf_bisect', 'win')
_AddTestSpec('winx64_10_perf_bisect', 'win')
_AddTestSpec('win_8_perf_bisect', 'win', target_bits=32)
_AddTestSpec('win_perf_bisect', 'win', target_bits=32)
_AddTestSpec('win_x64_perf_bisect', 'win')
_AddTestSpec('winx64ati_perf_bisect', 'win')
_AddTestSpec('winx64intel_perf_bisect', 'win')
_AddTestSpec('winx64nvidia_perf_bisect', 'win')

_AddTestSpec('mac_10_11_perf_bisect', 'mac')
_AddTestSpec('mac_10_12_perf_bisect', 'mac')
_AddTestSpec('mac_retina_perf_bisect', 'mac')
_AddTestSpec('mac_hdd_perf_bisect', 'mac')
_AddTestSpec('mac_pro_perf_bisect', 'mac')
_AddTestSpec('mac_air_perf_bisect', 'mac')

_AddTestSpec('linux_perf_bisect', 'linux')

_AddTestSpec('staging_linux_perf_bisect', 'linux')
_AddTestSpec('staging_mac_10_12_perf_bisect', 'mac')
_AddTestSpec('staging_win_perf_bisect', 'win', target_bits=32)
