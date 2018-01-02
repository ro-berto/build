# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import chromium_perf
from . import steps

import DEPS
CHROMIUM_CONFIG_CTX = DEPS['chromium'].CONFIG_CTX
GCLIENT_CONFIG_CTX = DEPS['gclient'].CONFIG_CTX


SPEC = {
  'builders': {},
  'settings': chromium_perf.SPEC['settings'],
}


@CHROMIUM_CONFIG_CTX(includes=['chromium_win_clang_official', 'mb'])
def chromium_perf_clang(c):
  pass


@GCLIENT_CONFIG_CTX(includes=['chromium_perf'])
def chromium_perf_clang(c):
  pass


def _AddBuildSpec(name, perf_id, platform, config_name='chromium_perf',
                  target_bits=64,
                  compile_targets=None, extra_compile_targets=None,
                  force_exparchive=False, run_sizes=True):
  SPEC['builders'][name] = chromium_perf.BuildSpec(
      config_name, perf_id, platform, target_bits,
      compile_targets=compile_targets,
      extra_compile_targets=extra_compile_targets,
      force_exparchive=force_exparchive, run_sizes=run_sizes)


def _AddIsolatedTestSpec(name, perf_id, platform,
                         parent_buildername=None, target_bits=64):
  spec = chromium_perf.TestSpec('chromium_perf', perf_id, platform, target_bits,
                                parent_buildername=parent_buildername)
  if not parent_buildername:
    spec['parent_mastername'] = 'chromium.perf'
  else:
    spec['parent_mastername'] = 'chromium.perf.fyi'

  SPEC['builders'][name] = spec


_AddBuildSpec('Android Builder FYI', 'android', 'android', target_bits=32,
              extra_compile_targets=['android_tools',
                                     'cc_perftests',
                                     'chrome_public_apk',
                                     'gpu_perftests',
                                     'push_apps_to_background_apk',
                                     'system_webview_apk',
                                     'system_webview_shell_apk',])

_AddIsolatedTestSpec('Android Nexus 5X Perf FYI', 'android-n5x-perf-fyi',
      'android', parent_buildername='Android Builder FYI', target_bits=32)

_AddBuildSpec('Android arm64 Builder FYI', 'android', 'android',
              extra_compile_targets=['android_tools',
                                     'cc_perftests',
                                     'chrome_public_apk',
                                     'gpu_perftests',
                                     'push_apps_to_background_apk',
                                     'system_webview_apk',
                                     'system_webview_shell_apk',])
_AddBuildSpec('Linux Compile FYI', 'linux-fyi', 'linux')


_AddBuildSpec('Win Builder FYI', 'win', 'win', force_exparchive=True)
_AddIsolatedTestSpec('Win 10 Low-End Perf Tests', 'win-10-low-end', 'win',
                     parent_buildername='Win Builder FYI')
_AddIsolatedTestSpec('Win 10 4 Core Low-End Perf Tests',
                     'win-10-4-core-low-end', 'win',
                     parent_buildername='Win Builder FYI')


_AddBuildSpec('Win Clang Builder', 'win-clang-builder', 'win',
              config_name='chromium_perf_clang', target_bits=32)

_AddIsolatedTestSpec('Mojo Linux Perf', 'mojo-linux-perf', 'linux')
_AddIsolatedTestSpec(
    'One Buildbot Step Test Builder', 'buildbot-test', 'linux',
    parent_buildername='Linux Compile FYI')

_AddBuildSpec('Battor Agent Linux', 'linux', 'linux', run_sizes=False,
              compile_targets=['battor_agent'])
_AddBuildSpec('Battor Agent Mac', 'mac', 'mac', run_sizes=False,
              compile_targets=['battor_agent'])
_AddBuildSpec('Battor Agent Win', 'win', 'win', run_sizes=False,
              compile_targets=['battor_agent'])

_AddIsolatedTestSpec('Histogram Pipeline Linux Perf',
                     'histogram-pipeline-linux-perf',
                     'linux')

_AddIsolatedTestSpec('Linux ChromeOS Perf (mus-viz)', 'chromeos-mus-viz-perf',
                     'linux')
