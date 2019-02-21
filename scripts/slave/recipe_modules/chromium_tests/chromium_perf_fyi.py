# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import chromium_perf
from . import steps

from RECIPE_MODULES.build.chromium import CONFIG_CTX as CHROMIUM_CONFIG_CTX
from RECIPE_MODULES.depot_tools.gclient import CONFIG_CTX as GCLIENT_CONFIG_CTX


SPEC = {
  'builders': {},
  'settings': chromium_perf.SPEC['settings'],
}


@CHROMIUM_CONFIG_CTX(includes=['chromium_win_clang_official', 'mb'])
def chromium_perf_clang(_):
  pass


@GCLIENT_CONFIG_CTX(includes=['chromium_perf'])
def chromium_perf_clang(_):
  pass


def _AddBuildSpec(name, platform, config_name='chromium_perf',
                  target_bits=64, compile_targets=None,
                  extra_compile_targets=None, force_exparchive=False,
                  run_sizes=True):
  SPEC['builders'][name] = chromium_perf.BuildSpec(
      config_name, platform, target_bits,
      compile_targets=compile_targets,
      extra_compile_targets=extra_compile_targets,
      force_exparchive=force_exparchive, run_sizes=run_sizes)


def _AddIsolatedTestSpec(name, platform,
                         parent_buildername=None, parent_mastername=None,
                         target_bits=64):
  spec = chromium_perf.TestSpec(
      'chromium_perf', platform, target_bits,
      parent_buildername=parent_buildername)
  if parent_mastername:
    spec['parent_mastername'] = parent_mastername

  SPEC['builders'][name] = spec


_AddIsolatedTestSpec('android-nexus5x-perf-fyi',
      'android', parent_buildername='android-builder-perf', target_bits=32,
      parent_mastername='chromium.perf')

_AddBuildSpec('android-cfi-builder-perf-fyi', 'android',
              target_bits=32,
              extra_compile_targets=['android_tools',
                                     'cc_perftests',
                                     'chrome_public_apk',
                                     'gpu_perftests',
                                     'push_apps_to_background_apk',
                                     'system_webview_apk',
                                     'system_webview_shell_apk',])

_AddBuildSpec('android_arm64-cfi-builder-perf-fyi', 'android',
              extra_compile_targets=['android_tools',
                                     'cc_perftests',
                                     'chrome_public_apk',
                                     'gpu_perftests',
                                     'push_apps_to_background_apk',
                                     'system_webview_apk',
                                     'system_webview_shell_apk',])

_AddIsolatedTestSpec('linux-perf-fyi', 'linux',
                     parent_buildername='linux-builder-perf',
                     parent_mastername='chromium.perf')

_AddIsolatedTestSpec('android-pixel2-perf', 'android',
                     target_bits=64,
                     parent_mastername='chromium.perf',
                     parent_buildername='android_arm64-builder-perf')
_AddIsolatedTestSpec('android-pixel2_webview-perf', 'android',
                     target_bits=64,
                     parent_mastername='chromium.perf',
                     parent_buildername='android_arm64-builder-perf')


_AddIsolatedTestSpec('win-10_laptop_high_end-perf_Lenovo-P51', 'win',
                     parent_buildername='win64-builder-perf',
                     parent_mastername='chromium.perf')

_AddIsolatedTestSpec('win-10_laptop_high_end-perf_Dell-Precision', 'win',
                     parent_buildername='win64-builder-perf',
                     parent_mastername='chromium.perf')

_AddIsolatedTestSpec('win-7_laptop_low_end_x32-perf_Acer-Aspire-5', 'win',
                     parent_buildername='win32-builder-perf',
                     parent_mastername='chromium.perf',
                     target_bits=32)

_AddIsolatedTestSpec('win-7_laptop_low_end_x32-perf_Dell-Latitude', 'win',
                     parent_buildername='win32-builder-perf',
                     parent_mastername='chromium.perf',
                     target_bits=32)

_AddIsolatedTestSpec('win-7_laptop_low_end_x32-perf-Lenovo-ThinkPad', 'win',
                     parent_buildername='win32-builder-perf',
                     parent_mastername='chromium.perf',
                     target_bits=32)
