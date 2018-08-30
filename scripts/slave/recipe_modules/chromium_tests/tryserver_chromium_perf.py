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
      'tryserver_chromium_perf', platform, target_bits,
      force_exparchive=False)


def _AddTestSpec(name, platform, target_bits=64):
   # parent_buildername is not used by the bisect or perf try recipes,
   # but required for running the chromium expectations tests.
   SPEC['builders'][name] = chromium_perf.TestSpec(
       'tryserver_chromium_perf', platform, target_bits,
       parent_buildername='dummy')


_AddBuildSpec('linux_perf_bisect_builder', 'linux')

_AddTestSpec('linux_fyi_perf_bisect', 'linux')
_AddTestSpec('linux_perf_bisect', 'linux')
_AddTestSpec('staging_linux_perf_bisect', 'linux')
